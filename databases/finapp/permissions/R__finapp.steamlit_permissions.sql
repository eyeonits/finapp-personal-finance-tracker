-- Streamlit apps are schema-level objects in Snowflake.
-- Therefore, they are located in a schema under a database.
-- They also rely on virtual warehouses to provide the compute resource.
-- We recommend starting with X-SMALL warehouses and upgrade when needed.

-- To help your team create Streamlit apps successfully, consider running the following script.
-- Please note that this is an example setup.
-- You can modify the script to suit your needs.
-- If you want all roles to create Streamlit apps in the PUBLIC schema, run
GRANT CREATE STREAMLIT ON SCHEMA FINAPP.STEAMLIT TO ROLE FINAPP_ROLE;
GRANT CREATE STAGE ON SCHEMA FINAPP.STEAMLIT TO ROLE FINAPP_ROLE;

-- Don't forget to grant USAGE on a warehouse.
GRANT USAGE ON WAREHOUSE FINAPP_WH TO ROLE FINAPP_ROLE;

-- If you only want certain roles to create Streamlit apps,
-- or want to enable a different location to store the Streamlit apps,
-- change the database, schema, and role names in the above commands.