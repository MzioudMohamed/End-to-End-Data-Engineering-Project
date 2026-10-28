-- Crée LegacyRetail : la base "legacy vivante" que le pipeline va migrer.
-- AdventureWorks2022 sert uniquement d'archive : on y copie l'état au 2014-04-30 (J0),
-- puis usp_advance_one_day (advance_one_day.sql) rejoue les jours suivants, un par un.
-- Rejouable : le script supprime et recrée LegacyRetail (remise à zéro de la simulation).

USE master;
GO
IF DB_ID(N'LegacyRetail') IS NOT NULL
BEGIN
    ALTER DATABASE LegacyRetail SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE LegacyRetail;
END
GO
CREATE DATABASE LegacyRetail;
GO
USE LegacyRetail;
GO

-- Toutes les tables portent ModifiedDate : c'est la colonne de watermark du chargement incrémental.
-- On ne reprend pas celle d'AdventureWorks (non fiable, voir journal) : on la maîtrise ici.

CREATE TABLE dbo.Territory (
    TerritoryID       int          NOT NULL PRIMARY KEY,
    Name              nvarchar(50) NOT NULL,
    CountryRegionCode nvarchar(3)  NOT NULL,
    TerritoryGroup    nvarchar(50) NOT NULL,
    ModifiedDate      datetime2(0) NOT NULL
);

CREATE TABLE dbo.ProductCategory (
    ProductCategoryID int          NOT NULL PRIMARY KEY,
    Name              nvarchar(50) NOT NULL,
    ModifiedDate      datetime2(0) NOT NULL
);

CREATE TABLE dbo.ProductSubcategory (
    ProductSubcategoryID int          NOT NULL PRIMARY KEY,
    ProductCategoryID    int          NOT NULL,
    Name                 nvarchar(50) NOT NULL,
    ModifiedDate         datetime2(0) NOT NULL
);

CREATE TABLE dbo.Product (
    ProductID            int           NOT NULL PRIMARY KEY,
    Name                 nvarchar(50)  NOT NULL,
    ProductNumber        nvarchar(25)  NOT NULL,
    Color                nvarchar(15)  NULL,
    StandardCost         decimal(19,4) NOT NULL,
    ListPrice            decimal(19,4) NOT NULL,
    ProductSubcategoryID int           NULL,
    ModifiedDate         datetime2(0)  NOT NULL
);

CREATE TABLE dbo.Customer (
    CustomerID   int           NOT NULL PRIMARY KEY,
    CustomerName nvarchar(160) NOT NULL,
    CustomerType varchar(10)   NOT NULL,   -- 'Individual' ou 'Store'
    TerritoryID  int           NULL,
    ModifiedDate datetime2(0)  NOT NULL
);

CREATE TABLE dbo.SalesOrderHeader (
    SalesOrderID    int           NOT NULL PRIMARY KEY,
    OrderDate       date          NOT NULL,
    CustomerID      int           NOT NULL,
    TerritoryID     int           NULL,
    OnlineOrderFlag bit           NOT NULL,
    SubTotal        decimal(19,4) NOT NULL,
    TaxAmt          decimal(19,4) NOT NULL,
    Freight         decimal(19,4) NOT NULL,
    ModifiedDate    datetime2(0)  NOT NULL
);

CREATE TABLE dbo.SalesOrderDetail (
    SalesOrderDetailID int           NOT NULL PRIMARY KEY,
    SalesOrderID       int           NOT NULL,
    ProductID          int           NOT NULL,
    OrderQty           smallint      NOT NULL,
    UnitPrice          decimal(19,4) NOT NULL,
    UnitPriceDiscount  decimal(19,4) NOT NULL,
    LineTotal          decimal(38,6) NOT NULL,
    ModifiedDate       datetime2(0)  NOT NULL
);

-- Petite table de contrôle : "où en est la simulation ?" (une seule ligne, Id = 1)
CREATE TABLE dbo.SimulationState (
    Id      int  NOT NULL PRIMARY KEY CHECK (Id = 1),
    LastDay date NOT NULL
);
GO

-- Chargement initial : l'état du système au jour J0.
-- Un seul batch (pas de GO) car les variables ne survivent pas à un GO.
DECLARE @J0    date         = '2014-04-30';
DECLARE @stamp datetime2(0) = CAST(@J0 AS datetime2(0));

-- Référentiels : copiés en entier, estampillés J0.
INSERT dbo.Territory (TerritoryID, Name, CountryRegionCode, TerritoryGroup, ModifiedDate)
SELECT TerritoryID, Name, CountryRegionCode, [Group], @stamp
FROM AdventureWorks2022.Sales.SalesTerritory;

INSERT dbo.ProductCategory (ProductCategoryID, Name, ModifiedDate)
SELECT ProductCategoryID, Name, @stamp
FROM AdventureWorks2022.Production.ProductCategory;

INSERT dbo.ProductSubcategory (ProductSubcategoryID, ProductCategoryID, Name, ModifiedDate)
SELECT ProductSubcategoryID, ProductCategoryID, Name, @stamp
FROM AdventureWorks2022.Production.ProductSubcategory;

INSERT dbo.Product (ProductID, Name, ProductNumber, Color, StandardCost, ListPrice, ProductSubcategoryID, ModifiedDate)
SELECT ProductID, Name, ProductNumber, Color, StandardCost, ListPrice, ProductSubcategoryID, @stamp
FROM AdventureWorks2022.Production.Product;

-- Clients : seulement ceux qui ont déjà commandé à J0. Les autres "arriveront" avec leur première commande.
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
                       WHERE OrderDate <= @J0);

-- Commandes de l'historique : ModifiedDate = jour de la commande (le legacy "saisit" la commande ce jour-là).
INSERT dbo.SalesOrderHeader (SalesOrderID, OrderDate, CustomerID, TerritoryID, OnlineOrderFlag,
                             SubTotal, TaxAmt, Freight, ModifiedDate)
SELECT SalesOrderID, CAST(OrderDate AS date), CustomerID, TerritoryID, OnlineOrderFlag,
       SubTotal, TaxAmt, Freight, CAST(OrderDate AS datetime2(0))
FROM AdventureWorks2022.Sales.SalesOrderHeader
WHERE OrderDate <= @J0;

INSERT dbo.SalesOrderDetail (SalesOrderDetailID, SalesOrderID, ProductID, OrderQty,
                             UnitPrice, UnitPriceDiscount, LineTotal, ModifiedDate)
SELECT d.SalesOrderDetailID, d.SalesOrderID, d.ProductID, d.OrderQty,
       d.UnitPrice, d.UnitPriceDiscount, d.LineTotal, CAST(h.OrderDate AS datetime2(0))
FROM AdventureWorks2022.Sales.SalesOrderDetail d
JOIN AdventureWorks2022.Sales.SalesOrderHeader h ON h.SalesOrderID = d.SalesOrderID
WHERE h.OrderDate <= @J0;

INSERT dbo.SimulationState (Id, LastDay) VALUES (1, @J0);
GO

-- Index sur la colonne de watermark : sans lui, chaque extraction incrémentale parcourt toute la table.
CREATE INDEX IX_Customer_ModifiedDate         ON dbo.Customer (ModifiedDate);
CREATE INDEX IX_Product_ModifiedDate          ON dbo.Product (ModifiedDate);
CREATE INDEX IX_SalesOrderHeader_ModifiedDate ON dbo.SalesOrderHeader (ModifiedDate);
CREATE INDEX IX_SalesOrderDetail_ModifiedDate ON dbo.SalesOrderDetail (ModifiedDate);
GO

-- Vérification : volumes après chargement initial
SELECT 'Territory' AS table_name, COUNT(*) AS row_count FROM dbo.Territory
UNION ALL SELECT 'ProductCategory',    COUNT(*) FROM dbo.ProductCategory
UNION ALL SELECT 'ProductSubcategory', COUNT(*) FROM dbo.ProductSubcategory
UNION ALL SELECT 'Product',            COUNT(*) FROM dbo.Product
UNION ALL SELECT 'Customer',           COUNT(*) FROM dbo.Customer
UNION ALL SELECT 'SalesOrderHeader',   COUNT(*) FROM dbo.SalesOrderHeader
UNION ALL SELECT 'SalesOrderDetail',   COUNT(*) FROM dbo.SalesOrderDetail;

SELECT LastDay FROM dbo.SimulationState;
GO