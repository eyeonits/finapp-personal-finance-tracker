import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import {
  recurringPaymentsApi,
  RecurringPayment,
  PaymentRecord,
  PaymentSummary,
  CreateRecurringPaymentRequest,
  UpdateRecurringPaymentRequest,
} from '../lib/api';
import { format, parseISO } from 'date-fns';

// Helper function to format currency
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

// Frequency display labels
const frequencyLabels: Record<string, string> = {
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
};

// Status badge colors
const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  paid: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  overdue: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  skipped: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
};

type TabType = 'overview' | 'bills' | 'upcoming' | 'history';

export default function RecurringPayments() {
  const { user, logout } = useAuth();
  const { isDarkMode, toggleDarkMode } = useTheme();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Data states
  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [payments, setPayments] = useState<RecurringPayment[]>([]);
  const [upcomingRecords, setUpcomingRecords] = useState<PaymentRecord[]>([]);
  const [overdueRecords, setOverdueRecords] = useState<PaymentRecord[]>([]);
  const [allRecords, setAllRecords] = useState<PaymentRecord[]>([]);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPayModal, setShowPayModal] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<RecurringPayment | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<PaymentRecord | null>(null);

  // Form states
  const [formData, setFormData] = useState<CreateRecurringPaymentRequest>({
    name: '',
    amount: 0,
    frequency: 'monthly',
    start_date: format(new Date(), 'yyyy-MM-dd'),
    due_day: 1,
    description: '',
    category: '',
    payee: '',
    auto_pay: false,
    notes: '',
  });

  const [payFormData, setPayFormData] = useState({
    paid_date: format(new Date(), 'yyyy-MM-dd'),
    amount_paid: 0,
  });

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [summaryData, paymentsData, upcomingData, overdueData] = await Promise.all([
        recurringPaymentsApi.getSummary(),
        recurringPaymentsApi.getRecurringPayments({ is_active: true }),
        recurringPaymentsApi.getUpcomingPayments(30),
        recurringPaymentsApi.getOverduePayments(),
      ]);

      setSummary(summaryData);
      setPayments(paymentsData.payments);
      setUpcomingRecords(upcomingData.records);
      setOverdueRecords(overdueData.records);
    } catch (err: any) {
      console.error('Error loading data:', err);
      setError(err.response?.data?.detail?.error?.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAllRecords = useCallback(async () => {
    try {
      const recordsData = await recurringPaymentsApi.getPaymentRecords({ limit: 100 });
      setAllRecords(recordsData.records);
    } catch (err: any) {
      console.error('Error loading records:', err);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadAllRecords();
    }
  }, [activeTab, loadAllRecords]);

  // Form handlers
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : 
               type === 'number' ? parseFloat(value) || 0 : value,
    }));
  };

  const handlePayInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    setPayFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value,
    }));
  };

  // CRUD handlers
  const handleCreatePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await recurringPaymentsApi.createRecurringPayment(formData);
      setSuccess('Recurring payment created successfully');
      setShowAddModal(false);
      resetForm();
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create payment');
    }
  };

  const handleUpdatePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPayment) return;
    setError('');
    try {
      await recurringPaymentsApi.updateRecurringPayment(selectedPayment.payment_id, formData as UpdateRecurringPaymentRequest);
      setSuccess('Recurring payment updated successfully');
      setShowEditModal(false);
      setSelectedPayment(null);
      resetForm();
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to update payment');
    }
  };

  const handleDeletePayment = async (paymentId: string) => {
    if (!confirm('Are you sure you want to delete this recurring payment? This will also delete all payment records.')) {
      return;
    }
    try {
      await recurringPaymentsApi.deleteRecurringPayment(paymentId);
      setSuccess('Recurring payment deleted successfully');
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to delete payment');
    }
  };

  const handleMarkPaid = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecord) return;
    setError('');
    try {
      await recurringPaymentsApi.markAsPaid(selectedRecord.record_id, payFormData);
      setSuccess('Payment marked as paid');
      setShowPayModal(false);
      setSelectedRecord(null);
      loadData();
      if (activeTab === 'history') loadAllRecords();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to mark payment as paid');
    }
  };

  const handleSkipPayment = async (recordId: string) => {
    if (!confirm('Are you sure you want to skip this payment?')) return;
    try {
      await recurringPaymentsApi.skipPayment(recordId);
      setSuccess('Payment skipped');
      loadData();
      if (activeTab === 'history') loadAllRecords();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to skip payment');
    }
  };

  const handleGenerateRecords = async (paymentId: string) => {
    try {
      const result = await recurringPaymentsApi.generateRecords(paymentId, 3);
      setSuccess(`Generated ${result.records.length} payment records`);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to generate records');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      amount: 0,
      frequency: 'monthly',
      start_date: format(new Date(), 'yyyy-MM-dd'),
      due_day: 1,
      description: '',
      category: '',
      payee: '',
      auto_pay: false,
      notes: '',
    });
  };

  const openEditModal = (payment: RecurringPayment) => {
    setSelectedPayment(payment);
    setFormData({
      name: payment.name,
      amount: payment.amount,
      frequency: payment.frequency,
      start_date: payment.start_date,
      due_day: payment.due_day,
      description: payment.description || '',
      category: payment.category || '',
      payee: payment.payee || '',
      auto_pay: payment.auto_pay,
      notes: payment.notes || '',
    });
    setShowEditModal(true);
  };

  const openPayModal = (record: PaymentRecord) => {
    setSelectedRecord(record);
    setPayFormData({
      paid_date: format(new Date(), 'yyyy-MM-dd'),
      amount_paid: typeof record.amount_due === 'string' ? parseFloat(record.amount_due) : record.amount_due,
    });
    setShowPayModal(true);
  };

  // Get payment name for a record
  const getPaymentName = (paymentId: string): string => {
    const payment = payments.find(p => p.payment_id === paymentId);
    return payment?.name || 'Unknown';
  };

  // Clear messages after timeout
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(''), 10000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  return (
    <div className={`min-h-screen ${isDarkMode ? 'dark bg-gray-900' : 'bg-gray-50'}`}>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Link to="/dashboard" className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bills & Subscriptions</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add Bill
              </button>
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {isDarkMode ? '☀️' : '🌙'}
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">{user?.email}</span>
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm text-red-600 hover:text-red-800 dark:text-red-400"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alerts */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg dark:bg-red-900 dark:border-red-700 dark:text-red-200">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg dark:bg-green-900 dark:border-green-700 dark:text-green-200">
            {success}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8">
            {(['overview', 'bills', 'upcoming', 'history'] as TabType[]).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && summary && (
              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Active Bills</div>
                    <div className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                      {summary.total_recurring_payments}
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Est. Monthly Total</div>
                    <div className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                      {formatCurrency(summary.estimated_monthly_total)}
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Upcoming (30 days)</div>
                    <div className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                      {formatCurrency(summary.upcoming_total)}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{summary.upcoming_count} payments</div>
                  </div>
                </div>

                {/* Overdue Alert */}
                {summary.overdue_count > 0 && (
                  <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
                    <div className="flex items-center">
                      <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <div className="ml-3">
                        <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                          {summary.overdue_count} Overdue Payment{summary.overdue_count > 1 ? 's' : ''}
                        </h3>
                        <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                          Total: {formatCurrency(summary.overdue_total)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Quick Actions */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Upcoming Payments</h3>
                  {upcomingRecords.length === 0 ? (
                    <p className="text-gray-500 dark:text-gray-400">No upcoming payments in the next 30 days</p>
                  ) : (
                    <div className="space-y-3">
                      {upcomingRecords.slice(0, 5).map(record => (
                        <div key={record.record_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                          <div>
                            <div className="font-medium text-gray-900 dark:text-white">{getPaymentName(record.payment_id)}</div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              Due: {format(parseISO(record.due_date), 'MMM d, yyyy')}
                            </div>
                          </div>
                          <div className="flex items-center space-x-3">
                            <div className="text-right">
                              <div className="font-medium text-gray-900 dark:text-white">
                                {formatCurrency(typeof record.amount_due === 'string' ? parseFloat(record.amount_due) : record.amount_due)}
                              </div>
                              <span className={`inline-flex px-2 py-0.5 text-xs rounded-full ${statusColors[record.status]}`}>
                                {record.status}
                              </span>
                            </div>
                            <button
                              onClick={() => openPayModal(record)}
                              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                            >
                              Pay
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Bills Tab */}
            {activeTab === 'bills' && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Amount</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Frequency</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Due Day</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Category</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Auto-Pay</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {payments.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                          No recurring payments yet. Click "Add Bill" to get started.
                        </td>
                      </tr>
                    ) : (
                      payments.map(payment => (
                        <tr key={payment.payment_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="px-6 py-4">
                            <div className="font-medium text-gray-900 dark:text-white">{payment.name}</div>
                            {payment.payee && <div className="text-sm text-gray-500 dark:text-gray-400">{payment.payee}</div>}
                          </td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{formatCurrency(payment.amount)}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{frequencyLabels[payment.frequency]}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{payment.due_day || '-'}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{payment.category || '-'}</td>
                          <td className="px-6 py-4">
                            {payment.auto_pay ? (
                              <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Yes</span>
                            ) : (
                              <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">No</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right space-x-2">
                            <button
                              onClick={() => handleGenerateRecords(payment.payment_id)}
                              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 text-sm"
                            >
                              Generate
                            </button>
                            <button
                              onClick={() => openEditModal(payment)}
                              className="text-gray-600 hover:text-gray-800 dark:text-gray-400 text-sm"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeletePayment(payment.payment_id)}
                              className="text-red-600 hover:text-red-800 dark:text-red-400 text-sm"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Upcoming Tab */}
            {activeTab === 'upcoming' && (
              <div className="space-y-6">
                {/* Overdue Section */}
                {overdueRecords.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-red-600 dark:text-red-400 mb-4">Overdue</h3>
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead className="bg-red-50 dark:bg-red-900/30">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Bill</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Due Date</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Amount</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                          {overdueRecords.map(record => (
                            <tr key={record.record_id}>
                              <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">{getPaymentName(record.payment_id)}</td>
                              <td className="px-6 py-4 text-red-600 dark:text-red-400">{format(parseISO(record.due_date), 'MMM d, yyyy')}</td>
                              <td className="px-6 py-4 text-gray-900 dark:text-white">{formatCurrency(typeof record.amount_due === 'string' ? parseFloat(record.amount_due) : record.amount_due)}</td>
                              <td className="px-6 py-4 text-right space-x-2">
                                <button onClick={() => openPayModal(record)} className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">Pay</button>
                                <button onClick={() => handleSkipPayment(record.record_id)} className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700">Skip</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Upcoming Section */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Upcoming (Next 30 Days)</h3>
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-900">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Bill</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Due Date</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Amount</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {upcomingRecords.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                              No upcoming payments. Generate records from the Bills tab.
                            </td>
                          </tr>
                        ) : (
                          upcomingRecords.map(record => (
                            <tr key={record.record_id}>
                              <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">{getPaymentName(record.payment_id)}</td>
                              <td className="px-6 py-4 text-gray-900 dark:text-white">{format(parseISO(record.due_date), 'MMM d, yyyy')}</td>
                              <td className="px-6 py-4 text-gray-900 dark:text-white">{formatCurrency(typeof record.amount_due === 'string' ? parseFloat(record.amount_due) : record.amount_due)}</td>
                              <td className="px-6 py-4">
                                <span className={`inline-flex px-2 py-0.5 text-xs rounded-full ${statusColors[record.status]}`}>
                                  {record.status}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right space-x-2">
                                <button onClick={() => openPayModal(record)} className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">Pay</button>
                                <button onClick={() => handleSkipPayment(record.record_id)} className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700">Skip</button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* History Tab */}
            {activeTab === 'history' && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Bill</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Due Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Paid Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Amount Due</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Amount Paid</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {allRecords.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                          No payment history yet.
                        </td>
                      </tr>
                    ) : (
                      allRecords.map(record => (
                        <tr key={record.record_id}>
                          <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">{getPaymentName(record.payment_id)}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{format(parseISO(record.due_date), 'MMM d, yyyy')}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{record.paid_date ? format(parseISO(record.paid_date), 'MMM d, yyyy') : '-'}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{formatCurrency(typeof record.amount_due === 'string' ? parseFloat(record.amount_due) : record.amount_due)}</td>
                          <td className="px-6 py-4 text-gray-900 dark:text-white">{record.amount_paid ? formatCurrency(typeof record.amount_paid === 'string' ? parseFloat(record.amount_paid) : record.amount_paid) : '-'}</td>
                          <td className="px-6 py-4">
                            <span className={`inline-flex px-2 py-0.5 text-xs rounded-full ${statusColors[record.status]}`}>
                              {record.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </main>

      {/* Add/Edit Modal */}
      {(showAddModal || showEditModal) && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => { setShowAddModal(false); setShowEditModal(false); resetForm(); }}></div>
            <div className="relative bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full p-6 shadow-xl">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                {showEditModal ? 'Edit Recurring Payment' : 'Add Recurring Payment'}
              </h3>
              <form onSubmit={showEditModal ? handleUpdatePayment : handleCreatePayment} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name *</label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="e.g., Netflix, Rent, Electric Bill"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Amount *</label>
                    <input
                      type="number"
                      name="amount"
                      value={formData.amount}
                      onChange={handleInputChange}
                      required
                      min="0.01"
                      step="0.01"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Frequency *</label>
                    <select
                      name="frequency"
                      value={formData.frequency}
                      onChange={handleInputChange}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    >
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="yearly">Yearly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start Date *</label>
                    <input
                      type="date"
                      name="start_date"
                      value={formData.start_date}
                      onChange={handleInputChange}
                      required
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due Day</label>
                    <input
                      type="number"
                      name="due_day"
                      value={formData.due_day || ''}
                      onChange={handleInputChange}
                      min="1"
                      max="31"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="1-31"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Category</label>
                    <input
                      type="text"
                      name="category"
                      value={formData.category || ''}
                      onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="e.g., Utilities, Entertainment"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Payee</label>
                    <input
                      type="text"
                      name="payee"
                      value={formData.payee || ''}
                      onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="e.g., Company name"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
                    <input
                      type="text"
                      name="description"
                      value={formData.description || ''}
                      onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        name="auto_pay"
                        checked={formData.auto_pay}
                        onChange={handleInputChange}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Auto-pay enabled</span>
                    </label>
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Notes</label>
                    <textarea
                      name="notes"
                      value={formData.notes || ''}
                      onChange={handleInputChange}
                      rows={2}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    ></textarea>
                  </div>
                </div>
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => { setShowAddModal(false); setShowEditModal(false); resetForm(); }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    {showEditModal ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Pay Modal */}
      {showPayModal && selectedRecord && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => { setShowPayModal(false); setSelectedRecord(null); }}></div>
            <div className="relative bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 shadow-xl">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Mark as Paid</h3>
              <form onSubmit={handleMarkPaid} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Bill</label>
                  <p className="mt-1 text-gray-900 dark:text-white">{getPaymentName(selectedRecord.payment_id)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due Date</label>
                  <p className="mt-1 text-gray-900 dark:text-white">{format(parseISO(selectedRecord.due_date), 'MMM d, yyyy')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Paid Date *</label>
                  <input
                    type="date"
                    name="paid_date"
                    value={payFormData.paid_date}
                    onChange={handlePayInputChange}
                    required
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Amount Paid *</label>
                  <input
                    type="number"
                    name="amount_paid"
                    value={payFormData.amount_paid}
                    onChange={handlePayInputChange}
                    required
                    min="0.01"
                    step="0.01"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  />
                </div>
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => { setShowPayModal(false); setSelectedRecord(null); }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                  >
                    Mark as Paid
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
