USE [master];
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.sql_logins
    WHERE name = N'adf_reader'
)
BEGIN
    CREATE LOGIN [adf_reader]
    WITH PASSWORD = N'REPLACE_WITH_A_STRONG_PASSWORD',
         CHECK_POLICY = ON,
         CHECK_EXPIRATION = ON;
END;
GO

USE [LegacyRetail];
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_principals
    WHERE name = N'adf_reader'
)
BEGIN
    CREATE USER [adf_reader]
    FOR LOGIN [adf_reader];
END;
GO

ALTER ROLE [db_datareader]
ADD MEMBER [adf_reader];
GO