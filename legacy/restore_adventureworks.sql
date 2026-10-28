-- Restaure la base legacy AdventureWorks2022 dans le conteneur SQL Server.
-- Prérequis : AdventureWorks2022.bak est dans legacy/backup/ (monté sur /backup dans le conteneur).

RESTORE FILELISTONLY FROM DISK = N'/backup/AdventureWorks2022.bak';
GO

IF DB_ID(N'AdventureWorks2022') IS NULL
BEGIN
    RESTORE DATABASE AdventureWorks2022
    FROM DISK = N'/backup/AdventureWorks2022.bak'
    WITH
        MOVE N'AdventureWorks2022'     TO N'/var/opt/mssql/data/AdventureWorks2022.mdf',
        MOVE N'AdventureWorks2022_log' TO N'/var/opt/mssql/data/AdventureWorks2022_log.ldf',
        STATS = 10;
END
ELSE
    PRINT 'AdventureWorks2022 existe déjà : restauration ignorée.';
GO

SELECT name, state_desc, compatibility_level
FROM sys.databases
WHERE name = N'AdventureWorks2022';
GO