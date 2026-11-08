USE [LegacyRetail];
GO

IF OBJECT_ID(N'dbo.EtlFullLoadConfig', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.EtlFullLoadConfig
    (
        ConfigId       int IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_EtlFullLoadConfig PRIMARY KEY,
        SourceSchema   sysname NOT NULL,
        SourceTable    sysname NOT NULL,
        ExtractColumns nvarchar(max) NOT NULL,
        IsActive       bit NOT NULL
            CONSTRAINT DF_EtlFullLoadConfig_IsActive DEFAULT (1),
        CONSTRAINT UQ_EtlFullLoadConfig_Source
            UNIQUE (SourceSchema, SourceTable)
    );
END;
GO

MERGE dbo.EtlFullLoadConfig AS target
USING
(
    VALUES
    (
        N'dbo',
        N'SalesOrderHeader',
        N'SalesOrderID, OrderDate, CustomerID, TerritoryID, OnlineOrderFlag, SubTotal, TaxAmt, Freight, ModifiedDate',
        1
    ),
    (
        N'dbo',
        N'Customer',
        N'CustomerID, CustomerName, CustomerType, TerritoryID, ModifiedDate',
        1
    ),
    (
        N'dbo',
        N'Product',
        N'ProductID, Name, ProductNumber, Color, StandardCost, ListPrice, ProductSubcategoryID, ModifiedDate',
        1
    ),
    (
        N'dbo',
        N'ProductCategory',
        N'ProductCategoryID, Name, ModifiedDate',
        1
    ),
    (
        N'dbo',
        N'ProductSubcategory',
        N'ProductSubcategoryID, ProductCategoryID, Name, ModifiedDate',
        1
    ),
    (
        N'dbo',
        N'Territory',
        N'TerritoryID, Name, CountryRegionCode, TerritoryGroup, ModifiedDate',
        1
    )
) AS source
(
    SourceSchema,
    SourceTable,
    ExtractColumns,
    IsActive
)
ON target.SourceSchema = source.SourceSchema
AND target.SourceTable = source.SourceTable
WHEN MATCHED THEN
    UPDATE SET
        ExtractColumns = source.ExtractColumns,
        IsActive = source.IsActive
WHEN NOT MATCHED THEN
    INSERT
    (
        SourceSchema,
        SourceTable,
        ExtractColumns,
        IsActive
    )
    VALUES
    (
        source.SourceSchema,
        source.SourceTable,
        source.ExtractColumns,
        source.IsActive
    );

SELECT
    ConfigId,
    SourceSchema,
    SourceTable,
    ExtractColumns,
    IsActive
FROM dbo.EtlFullLoadConfig
ORDER BY ConfigId;
GO