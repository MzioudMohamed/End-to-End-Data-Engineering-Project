USE [LegacyRetail];
GO

IF OBJECT_ID(N'dbo.EtlTableConfig', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.EtlTableConfig
    (
        ConfigId          int IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_EtlTableConfig PRIMARY KEY,
        SourceSchema      sysname NOT NULL,
        SourceTable       sysname NOT NULL,
        LoadType          varchar(10) NOT NULL,
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
        (N'dbo', N'SalesOrderHeader', 'incremental', N'ModifiedDate', 1)
) AS source
(
    SourceSchema,
    SourceTable,
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
        LoadType,
        WatermarkColumn,
        IsActive
    )
    VALUES
    (
        source.SourceSchema,
        source.SourceTable,
        source.LoadType,
        source.WatermarkColumn,
        source.IsActive
    );
GO

SELECT
    ConfigId,
    SourceSchema,
    SourceTable,
    LoadType,
    WatermarkColumn,
    IsActive
FROM dbo.EtlTableConfig;
GO