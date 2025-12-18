import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { importsApi, ImportResponse } from '../lib/api';

export default function Import() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'credit_card' | 'bank'>('credit_card');
  
  // Credit card form state
  const [ccFile, setCcFile] = useState<File | null>(null);
  const [ccAccountId, setCcAccountId] = useState('');
  const [ccLoading, setCcLoading] = useState(false);
  const [ccError, setCcError] = useState('');
  const [ccSuccess, setCcSuccess] = useState<ImportResponse | null>(null);
  
  // Bank form state
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [bankAccountId, setBankAccountId] = useState('');
  const [bankLoading, setBankLoading] = useState(false);
  const [bankError, setBankError] = useState('');
  const [bankSuccess, setBankSuccess] = useState<ImportResponse | null>(null);

  const handleCreditCardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCcError('');
    setCcSuccess(null);

    if (!ccFile) {
      setCcError('Please select a CSV file');
      return;
    }

    if (!ccAccountId.trim()) {
      setCcError('Please enter an account ID (e.g., cc_apple, cc_chase)');
      return;
    }

    setCcLoading(true);

    try {
      const result = await importsApi.importCreditCard(ccFile, ccAccountId.trim());
      setCcSuccess(result);
      // Reset form
      setCcFile(null);
      setCcAccountId('');
    } catch (err: any) {
      console.error('Import error:', err);
      const errorMessage = err.response?.data?.detail 
        || err.response?.data?.message
        || err.message
        || 'Import failed. Please try again.';
      setCcError(errorMessage);
    } finally {
      setCcLoading(false);
    }
  };

  const handleBankSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBankError('');
    setBankSuccess(null);

    if (!bankFile) {
      setBankError('Please select a CSV file');
      return;
    }

    if (!bankAccountId.trim()) {
      setBankError('Please enter an account ID (e.g., chk_main, sav_main)');
      return;
    }

    setBankLoading(true);

    try {
      const result = await importsApi.importBank(bankFile, bankAccountId.trim());
      setBankSuccess(result);
      // Reset form
      setBankFile(null);
      setBankAccountId('');
    } catch (err: any) {
      console.error('Import error:', err);
      const errorMessage = err.response?.data?.detail 
        || err.response?.data?.message
        || err.message
        || 'Import failed. Please try again.';
      setBankError(errorMessage);
    } finally {
      setBankLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <nav className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link to="/dashboard" className="text-xl font-bold text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400">
                🏦 FinApp
              </Link>
              <span className="text-gray-400 dark:text-gray-500">|</span>
              <span className="text-sm text-gray-700 dark:text-gray-300">Import Transactions</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/dashboard"
                className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300"
              >
                ← Back to Dashboard
              </Link>
              <span className="text-sm text-gray-700 dark:text-gray-300">{user?.email}</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Import Transactions</h2>

          {/* Tabs */}
          <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('credit_card')}
                className={`${
                  activeTab === 'credit_card'
                    ? 'border-indigo-500 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Credit Card
              </button>
              <button
                onClick={() => setActiveTab('bank')}
                className={`${
                  activeTab === 'bank'
                    ? 'border-indigo-500 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Bank
              </button>
            </nav>
          </div>

          {/* Credit Card Import Form */}
          {activeTab === 'credit_card' && (
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Import Credit Card CSV</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Upload a credit card CSV file. Supports multiple formats:
                <ul className="list-disc list-inside mt-2 space-y-1 text-gray-600 dark:text-gray-400">
                  <li>Standard format: transaction date, post date, description, category, type, amount, memo</li>
                  <li>Apple Card format: Transaction Date, Clearing Date, Description, Merchant, Category, Type, Amount (USD)</li>
                  <li>Simple Date/Amount format (e.g., Amex): Date, Description, Amount, Category</li>
                </ul>
              </p>

              {ccError && (
                <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4 mb-4">
                  <div className="text-sm text-red-800 dark:text-red-400">{ccError}</div>
                </div>
              )}

              {ccSuccess && (
                <div className="rounded-md bg-green-50 dark:bg-green-900/20 p-4 mb-4">
                  <div className="text-sm font-medium text-green-800 dark:text-green-400 mb-2">Import completed successfully!</div>
                  <div className="text-sm text-green-700 dark:text-green-300">
                    <p>Total rows: {ccSuccess.rows_total}</p>
                    <p>Inserted: {ccSuccess.rows_inserted}</p>
                    <p>Skipped (duplicates): {ccSuccess.rows_skipped}</p>
                    <p>Status: {ccSuccess.status}</p>
                  </div>
                </div>
              )}

              <form onSubmit={handleCreditCardSubmit} className="space-y-4">
                <div>
                  <label htmlFor="cc-file" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    CSV File
                  </label>
                  <input
                    id="cc-file"
                    type="file"
                    accept=".csv"
                    onChange={(e) => setCcFile(e.target.files?.[0] || null)}
                    className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 dark:file:bg-indigo-900 file:text-indigo-700 dark:file:text-indigo-300 hover:file:bg-indigo-100 dark:hover:file:bg-indigo-800"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="cc-account-id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Account ID
                  </label>
                  <input
                    id="cc-account-id"
                    type="text"
                    value={ccAccountId}
                    onChange={(e) => setCcAccountId(e.target.value)}
                    placeholder="e.g., cc_apple, cc_chase"
                    className="mt-1 block w-full border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm px-3 py-2 border"
                    required
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    A unique identifier for this account (e.g., cc_apple, cc_chase)
                  </p>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={ccLoading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {ccLoading ? 'Importing...' : 'Import Credit Card CSV'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Bank Import Form */}
          {activeTab === 'bank' && (
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Import Bank CSV</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Upload a bank CSV file. Required columns (case-insensitive):
                <ul className="list-disc list-inside mt-2 space-y-1 text-gray-600 dark:text-gray-400">
                  <li>Posted Date</li>
                  <li>Effective Date</li>
                  <li>Transaction</li>
                  <li>Amount</li>
                  <li>Balance</li>
                  <li>Description</li>
                  <li>Check#</li>
                  <li>Memo</li>
                </ul>
              </p>

              {bankError && (
                <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4 mb-4">
                  <div className="text-sm text-red-800 dark:text-red-400">{bankError}</div>
                </div>
              )}

              {bankSuccess && (
                <div className="rounded-md bg-green-50 dark:bg-green-900/20 p-4 mb-4">
                  <div className="text-sm font-medium text-green-800 dark:text-green-400 mb-2">Import completed successfully!</div>
                  <div className="text-sm text-green-700 dark:text-green-300">
                    <p>Total rows: {bankSuccess.rows_total}</p>
                    <p>Inserted: {bankSuccess.rows_inserted}</p>
                    <p>Skipped (duplicates): {bankSuccess.rows_skipped}</p>
                    <p>Status: {bankSuccess.status}</p>
                  </div>
                </div>
              )}

              <form onSubmit={handleBankSubmit} className="space-y-4">
                <div>
                  <label htmlFor="bank-file" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    CSV File
                  </label>
                  <input
                    id="bank-file"
                    type="file"
                    accept=".csv"
                    onChange={(e) => setBankFile(e.target.files?.[0] || null)}
                    className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 dark:file:bg-indigo-900 file:text-indigo-700 dark:file:text-indigo-300 hover:file:bg-indigo-100 dark:hover:file:bg-indigo-800"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="bank-account-id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Account ID
                  </label>
                  <input
                    id="bank-account-id"
                    type="text"
                    value={bankAccountId}
                    onChange={(e) => setBankAccountId(e.target.value)}
                    placeholder="e.g., chk_main, sav_main"
                    className="mt-1 block w-full border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm px-3 py-2 border"
                    required
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    A unique identifier for this account (e.g., chk_main, sav_main)
                  </p>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={bankLoading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {bankLoading ? 'Importing...' : 'Import Bank CSV'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


