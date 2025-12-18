CREATE OR ALTER TABLE FIN.CC_TRANSACTIONS (
  TRANSACTION_ID    STRING DEFAULT UUID_STRING() PRIMARY KEY,  -- unique ID
  TRANSACTION_DATE  DATE,               -- when it happened (if available)
  POST_DATE         DATE,               -- when it posted
  DESCRIPTION       VARCHAR(255),       -- merchant line, e.g., "NETFLIX.COM ..."
  CATEGORY          VARCHAR(100),       -- bank-provided category if any
  TYPE              VARCHAR(50),        -- e.g., 'debit', 'credit', 'payment'
  AMOUNT            NUMBER(18, 2),      -- negative = money out, positive = in
  MEMO              VARCHAR(255),       -- extra notes
  -- optional metadata
  ACCOUNT_ID        VARCHAR(100),       -- add this if possible (which card/checking)
  LOAD_TS           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
