USE [LegacyRetail];
GO

IF OBJECT_ID(N'dbo.EtlTableConfig', N'U') IS NOT NULL
    DROP TABLE dbo.EtlTableConfig;
GO

BEGIN
    CREATE TABLE dbo.EtlTableConfig
    (
        ConfigId          int IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_EtlTableConfig PRIMARY KEY,
        SourceSchema      sysname NOT NULL,
        SourceTable       sysname NOT NULL,
        ExtractColumns    nvarchar(max) NOT NULL,
        LoadType          varchar(20) NOT NULL,
        WatermarkColumn   sysname NULL,
        IsActive           bit NOT NULL
            CONSTRAINT DF_EtlTableConfig_IsActive DEFAULT (1),
        CONSTRAINT UQ_EtlTableConfig_Source
            UNIQUE (SourceSchema, SourceTable),
        CONSTRAINT CK_EtlTableConfig_LoadType
            CHECK (LoadType IN ('full', 'incremental'))
    );
END;
GO

MERGE dbo.EtlTableConfig AS target
USING
(
    VALUES
        (N'dbo', N'SalesOrderHeader', N'SalesOrderID, OrderDate, CustomerID, TerritoryID, OnlineOrderFlag, SubTotal, TaxAmt, Freight, ModifiedDate','incremental', N'ModifiedDate', 1),
        (N'dbo', N'Customer', N'CustomerID, CustomerName, CustomerType, TerritoryID, ModifiedDate', 'incremental', N'ModifiedDate', 1),
        (N'dbo', N'Product', N'ProductID, Name, ProductNumber, Color, StandardCost, ListPrice, ProductSubcategoryID, ModifiedDate', 'incremental', N'ModifiedDate', 1)
) AS source
(
    SourceSchema,
    SourceTable,
    ExtractColumns,
    LoadType,
    WatermarkColumn,
    IsActive
)
ON target.SourceSchema = source.SourceSchema
AND target.SourceTable = source.SourceTable
WHEN MATCHED THEN
    UPDATE SET
        LoadType = source.LoadType,
        WatermarkColumn = source.WatermarkColumn,
        IsActive = source.IsActive
WHEN NOT MATCHED THEN
    INSERT
    (
        SourceSchema,
        SourceTable,
        ExtractColumns,
        LoadType,
        WatermarkColumn,
        IsActive
    )
    VALUES
    (
        source.SourceSchema,
        source.SourceTable,
        source.ExtractColumns,
        source.LoadType,
        source.WatermarkColumn,
        source.IsActive
    );
GO

SELECT
    ConfigId,
    SourceSchema,
    SourceTable,
    ExtractColumns,
    LoadType,
    WatermarkColumn,
    IsActive
FROM dbo.EtlTableConfig;
GO