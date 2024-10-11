CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;


DROP TABLE IF EXISTS item_emb;
CREATE TABLE IF NOT EXISTS item_emb (
    id VARCHAR PRIMARY KEY,
    embedding VECTOR(32)
);

SELECT aws_s3.table_import_from_s3(
    'item_emb',
    'id,embedding',
    '(format csv, header true)',
    'de-c1w4-905418182499-us-east-1-ml-artifacts',
    'embeddings/item_embeddings.csv',
    'us-east-1'
);


DROP TABLE IF EXISTS user_emb;
CREATE TABLE IF NOT EXISTS user_emb (
    id INT PRIMARY KEY,
    embedding VECTOR(32)
);

SELECT aws_s3.table_import_from_s3(
    'user_emb',
    'id,embedding',
    '(format csv, header true)',
    'de-c1w4-905418182499-us-east-1-ml-artifacts',
    'embeddings/user_embeddings.csv',
    'us-east-1'
);
