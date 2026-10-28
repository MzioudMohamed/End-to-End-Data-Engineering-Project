-- Fait "passer un jour" dans le système legacy LegacyRetail.
-- Chaque appel rejoue, depuis l'archive AdventureWorks2022, le jour qui suit SimulationState.LastDay :
--   nouveaux clients, nouvelles commandes, puis quelques modifications de données existantes
--   (elles alimenteront le SCD2 plus tard).
-- Tout se passe dans une transaction : en cas d'erreur, rien n'est rejoué à moitié et le jour n'avance pas.

USE LegacyRetail;
GO

CREATE OR ALTER PROCEDURE dbo.usp_advance_one_day
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;   -- toute erreur annule la transaction en cours

    DECLARE @day date = (SELECT DATEADD(DAY, 1, LastDay) FROM dbo.SimulationState WHERE Id = 1);

    IF @day > (SELECT MAX(CAST(OrderDate AS date)) FROM AdventureWorks2022.Sales.SalesOrderHeader)
    BEGIN
        THROW 50001, N'Plus de jours à rejouer : archive AdventureWorks2022 épuisée.', 1;
    END;

    -- ModifiedDate de tout ce qui change ce jour-là (minuit du jour simulé)
    DECLARE @stamp datetime2(0) = CAST(@day AS datetime2(0));
    DECLARE @new_customers int, @orders int, @lines int, @moved_customers int, @repriced_products int;

    BEGIN TRANSACTION;

    -- 1) Nouveaux clients : ceux qui commandent ce jour-là et n'existent pas encore dans LegacyRetail.
    --    Ils doivent exister avant leurs commandes.
    INSERT dbo.Customer (CustomerID, CustomerName, CustomerType, TerritoryID, ModifiedDate)
    SELECT c.CustomerID,
           COALESCE(CASE WHEN c.StoreID IS NOT NULL THEN s.Name
                         ELSE p.FirstName + N' ' + p.LastName END, N'Unknown'),
           CASE WHEN c.StoreID IS NOT NULL THEN 'Store' ELSE 'Individual' END,
           c.TerritoryID,
           @stamp
    FROM AdventureWorks2022.Sales.Customer c
    LEFT JOIN AdventureWorks2022.Sales.Store s   ON s.BusinessEntityID = c.StoreID
    LEFT JOIN AdventureWorks2022.Person.Person p ON p.BusinessEntityID = c.PersonID
    WHERE c.CustomerID IN (SELECT CustomerID
                           FROM AdventureWorks2022.Sales.SalesOrderHeader
                           WHERE CAST(OrderDate AS date) = @day)
      AND NOT EXISTS (SELECT 1 FROM dbo.Customer x WHERE x.CustomerID = c.CustomerID);
    SET @new_customers = @@ROWCOUNT;

    -- 2) Commandes du jour (en-têtes puis lignes)
    INSERT dbo.SalesOrderHeader (SalesOrderID, OrderDate, CustomerID, TerritoryID, OnlineOrderFlag,
                                 SubTotal, TaxAmt, Freight, ModifiedDate)
    SELECT SalesOrderID, CAST(OrderDate AS date), CustomerID, TerritoryID, OnlineOrderFlag,
           SubTotal, TaxAmt, Freight, @stamp
    FROM AdventureWorks2022.Sales.SalesOrderHeader
    WHERE CAST(OrderDate AS date) = @day;
    SET @orders = @@ROWCOUNT;

    INSERT dbo.SalesOrderDetail (SalesOrderDetailID, SalesOrderID, ProductID, OrderQty,
                                 UnitPrice, UnitPriceDiscount, LineTotal, ModifiedDate)
    SELECT d.SalesOrderDetailID, d.SalesOrderID, d.ProductID, d.OrderQty,
           d.UnitPrice, d.UnitPriceDiscount, d.LineTotal, @stamp
    FROM AdventureWorks2022.Sales.SalesOrderDetail d
    JOIN AdventureWorks2022.Sales.SalesOrderHeader h ON h.SalesOrderID = d.SalesOrderID
    WHERE CAST(h.OrderDate AS date) = @day;
    SET @lines = @@ROWCOUNT;

    -- 3) Modification : 15 clients changent de territoire (futur SCD2 de la dimension client).
    --    CHECKSUM(..., @day) choisit des lignes différentes chaque jour, mais de façon reproductible.
    --    Les territoires vont de 1 à 10 : "% 10 + 1" donne toujours une valeur différente de l'actuelle.
    UPDATE dbo.Customer
    SET TerritoryID  = TerritoryID % 10 + 1,
        ModifiedDate = @stamp
    WHERE CustomerID IN (SELECT TOP (15) CustomerID
                         FROM dbo.Customer
                         WHERE TerritoryID IS NOT NULL
                         ORDER BY CHECKSUM(CustomerID, @day));
    SET @moved_customers = @@ROWCOUNT;

    -- 4) Modification : 3 produits vendables augmentent de 5 % (futur SCD2 de la dimension produit).
    UPDATE dbo.Product
    SET ListPrice    = ROUND(ListPrice * 1.05, 2),
        ModifiedDate = @stamp
    WHERE ProductID IN (SELECT TOP (3) ProductID
                        FROM dbo.Product
                        WHERE ListPrice > 0
                        ORDER BY CHECKSUM(ProductID, @day));
    SET @repriced_products = @@ROWCOUNT;

    -- 5) Le jour est entièrement rejoué : on le note.
    UPDATE dbo.SimulationState SET LastDay = @day WHERE Id = 1;

    COMMIT TRANSACTION;

    -- Résumé du jour rejoué
    SELECT @day AS simulated_day,
           @new_customers AS new_customers,
           @orders AS orders,
           @lines AS order_lines,
           @moved_customers AS customers_moved,
           @repriced_products AS products_repriced;
END;
GO