CREATE OR ALTER TABLE FIN.BANK_TRANSACTIONS (
  TRANSACTION_ID      STRING DEFAULT UUID_STRING() PRIMARY KEY,  -- unique ID
  POSTED_DATE         DATE NOT NULL,
  EFFECTIVE_DATE      DATE,
  DESCRIPTION         VARCHAR(255),
  TRANSACTION_TYPE    VARCHAR(50),       -- 'debit', 'credit', 'fee', etc.
  AMOUNT              NUMBER(18, 2),     -- negative = out, positive = in
  RUNNING_BALANCE     NUMBER(18, 2),
  CHECK_NUMBER        VARCHAR(50),
  MEMO                VARCHAR(255),
  ACCOUNT_ID          VARCHAR(100),       -- add this if possible (which card/checking)
  LOAD_TS             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
