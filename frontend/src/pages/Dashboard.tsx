import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { transactionsApi, Transaction, healthApi, HealthCheckResponse, ReadinessCheckResponse } from '../lib/api';
import { format, parseISO, startOfYear, startOfMonth, endOfMonth, subMonths, getYear, differenceInDays } from 'date-fns';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

type TabType = 'overview' | 'transactions' | 'ytd' | 'monthly' | 'categories' | 'housing' | 'trends' | 'validation' | 'health';

// Helper function to format currency with commas
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { isDarkMode, toggleDarkMode } = useTheme();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
  const [filteredTransactions, setFilteredTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState<string>('');
  const [error, setError] = useState('');
  const [healthData, setHealthData] = useState<{
    health: HealthCheckResponse | null;
    readiness: ReadinessCheckResponse | null;
    healthLoading: boolean;
    healthError: string;
    lastChecked: Date | null;
  }>({
    health: null,
    readiness: null,
    healthLoading: false,
    healthError: '',
    lastChecked: null,
  });
  const [filters, setFilters] = useState({
    start_date: format(new Date(Date.now() - 90 * 24 * 60 * 60 * 1000), 'yyyy-MM-dd'),
    end_date: format(new Date(), 'yyyy-MM-dd'),
    description: '',
    category: '',
    account_id: '',
    amount_min: '',
    amount_max: '',
  });

  // Load all transactions for YTD and other calculations (with pagination)
  const loadAllTransactions = useCallback(async () => {
    setLoading(true);
    setError('');
    setLoadingProgress('');
    try {
      const params: any = {
        start_date: format(startOfYear(new Date()), 'yyyy-MM-dd'),
        end_date: format(new Date(), 'yyyy-MM-dd'),
      };
      console.log('Loading all transactions with params:', params);
      console.log('This may take a moment if you have many transactions...');
      setLoadingProgress('Starting to load transactions...');
      
      // Try to load all transactions with pagination
      try {
        const data = await transactionsApi.getAllTransactions(params);
        console.log('Loaded all transactions:', data?.length || 0);
        setAllTransactions(data || []);
        setLoadingProgress('');
        
        if (!data || data.length === 0) {
          setError('No transactions found. Try importing some transactions first.');
        }
      } catch (paginationError: any) {
        console.warn('Pagination failed, falling back to single request:', paginationError);
        // Fallback: try loading just the first page
        setLoadingProgress('Loading first page of transactions...');
        const fallbackData = await transactionsApi.getTransactions({
          ...params,
          limit: 1000,
        });
        console.log('Loaded transactions (fallback):', fallbackData?.length || 0);
        setAllTransactions(fallbackData || []);
        setLoadingProgress('');
        
        if (fallbackData && fallbackData.length > 0) {
          setError(`Warning: Only loaded first ${fallbackData.length} transactions. There may be more. Check console for details.`);
        } else {
          setError('No transactions found. Try importing some transactions first.');
        }
      }
    } catch (err: any) {
      console.error('Error loading all transactions:', err);
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        stack: err.stack,
      });
      setLoadingProgress('');
      
      const errorMessage = err.response?.data?.detail?.error?.message 
        || err.response?.data?.detail 
        || err.response?.data?.message
        || err.message
        || 'Failed to load transactions. Please check if the API is running.';
      setError(errorMessage);
      
      if (err.response?.status === 401) {
        return;
      }
    } finally {
      setLoading(false);
      setLoadingProgress('');
    }
  }, []);

  // Load filtered transactions for the transactions tab
  const loadFilteredTransactions = useCallback(async () => {
    setError('');
    try {
      const params: any = {
        start_date: filters.start_date,
        end_date: filters.end_date,
      };
      if (filters.description) params.description = filters.description;
      if (filters.category) params.category = filters.category;
      if (filters.account_id) params.account_id = filters.account_id;
      if (filters.amount_min !== '') params.amount_min = parseFloat(filters.amount_min);
      if (filters.amount_max !== '') params.amount_max = parseFloat(filters.amount_max);

      const data = await transactionsApi.getTransactions(params);
      setFilteredTransactions(data || []);
    } catch (err: any) {
      console.error('Error loading transactions:', err);
      const errorMessage = err.response?.data?.detail?.error?.message 
        || err.response?.data?.detail 
        || err.response?.data?.message
        || err.message
        || 'Failed to load transactions';
      setError(errorMessage);
      
      if (err.response?.status === 401) {
        return;
      }
    }
  }, [filters.start_date, filters.end_date, filters.description, filters.category, filters.account_id, filters.amount_min, filters.amount_max]);

  useEffect(() => {
    loadAllTransactions();
  }, [loadAllTransactions]);

  useEffect(() => {
    if (activeTab === 'transactions') {
      loadFilteredTransactions();
    }
  }, [activeTab, loadFilteredTransactions]);

  const handleFilterChange = (field: string, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  // Use allTransactions for overview/analytics, filteredTransactions for transactions tab
  const transactions = activeTab === 'transactions' ? filteredTransactions : (allTransactions || []);

  // Calculate various metrics
  const metrics = useMemo(() => {
    const now = new Date();
    const yearStart = startOfYear(now);
    const monthStart = startOfMonth(now);
    const lastMonthStart = startOfMonth(subMonths(now, 1));
    const lastMonthEnd = endOfMonth(subMonths(now, 1));
    
    // Filter transactions by date
    const getTransactionsInRange = (start: Date, end: Date) => {
      return transactions.filter((t) => {
        try {
          const dateStr = typeof t.transaction_date === 'string' 
            ? t.transaction_date 
            : format(new Date(t.transaction_date), 'yyyy-MM-dd');
          const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
          return date >= start && date <= end;
        } catch {
          return false;
        }
      });
    };

    const ytdTransactions = getTransactionsInRange(yearStart, now);
    const thisMonthTransactions = getTransactionsInRange(monthStart, now);
    const lastMonthTransactions = getTransactionsInRange(lastMonthStart, lastMonthEnd);
    const last90DaysTransactions = getTransactionsInRange(subMonths(now, 3), now);

    const calculateTotals = (txns: Transaction[]) => {
      // Credit card spending = negative amounts from non-checking accounts
      const ccSpent = txns
        .filter((t) => t && typeof t.amount === 'number' && t.amount < 0 && t.account_id !== 'chk_main')
        .reduce((sum, t) => sum + Math.abs(t.amount), 0);
      
      // Checking outflows = negative amounts from chk_main (bill payments, transfers out, etc.)
      const checkingOut = txns
        .filter((t) => t && typeof t.amount === 'number' && t.amount < 0 && t.account_id === 'chk_main')
        .reduce((sum, t) => sum + Math.abs(t.amount), 0);
      
      // Total spending (all negative amounts)
      const totalSpent = txns
        .filter((t) => t && typeof t.amount === 'number' && t.amount < 0)
        .reduce((sum, t) => sum + Math.abs(t.amount), 0);
      
      // Only count income from chk_main account (actual income deposits)
      const received = txns
        .filter((t) => t && typeof t.amount === 'number' && t.amount > 0 && t.account_id === 'chk_main')
        .reduce((sum, t) => sum + t.amount, 0);
      
      return { 
        spent: ccSpent,           // Credit card spending only
        checkingOut,              // Checking account outflows
        totalSpent,               // All spending combined
        received,                 // Income (checking deposits)
        net: received - totalSpent,  // Net flow
        count: txns.length 
      };
    };

    const ytd = calculateTotals(ytdTransactions);
    const thisMonth = calculateTotals(thisMonthTransactions);
    const lastMonth = calculateTotals(lastMonthTransactions);
    const last90Days = calculateTotals(last90DaysTransactions);

    // Calculate daily averages (based on credit card spending)
    const daysInYear = differenceInDays(now, yearStart) + 1;
    const daysInMonth = differenceInDays(now, monthStart) + 1;
    const ytdDailyAvg = ytd.spent / daysInYear;
    const monthDailyAvg = thisMonth.spent / daysInMonth;

    // Projected annual spending (credit card only)
    const projectedAnnual = (ytd.spent / daysInYear) * 365;

    // Month-over-month change (credit card spending)
    const momChange = lastMonth.spent > 0 
      ? ((thisMonth.spent - lastMonth.spent) / lastMonth.spent) * 100 
      : 0;

    return {
      ytd,
      thisMonth,
      lastMonth,
      last90Days,
      ytdDailyAvg,
      monthDailyAvg,
      projectedAnnual,
      momChange,
      daysInYear,
      daysInMonth,
    };
  }, [transactions]);

  // Chart data calculations
  const chartData = useMemo(() => {
    // Category breakdown
    const categorySpending = transactions
      .filter((t) => t && typeof t.amount === 'number' && t.amount < 0)
      .reduce((acc, t) => {
        const category = t.category || 'Uncategorized';
        acc[category] = (acc[category] || 0) + Math.abs(t.amount);
        return acc;
      }, {} as Record<string, number>);

    const categoryEntries = Object.entries(categorySpending)
      .sort((a, b) => b[1] - a[1]);

    // Monthly spending (last 12 months)
    const monthlySpending = transactions
      .filter((t) => t && typeof t.amount === 'number' && t.amount < 0)
      .reduce((acc, t) => {
        try {
          const dateStr = typeof t.transaction_date === 'string' 
            ? t.transaction_date 
            : format(new Date(t.transaction_date), 'yyyy-MM-dd');
          const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
          const month = format(date, 'yyyy-MM');
          acc[month] = (acc[month] || 0) + Math.abs(t.amount);
          return acc;
        } catch {
          return acc;
        }
      }, {} as Record<string, number>);

    // Get last 12 months
    const months: string[] = [];
    for (let i = 11; i >= 0; i--) {
      const monthDate = subMonths(new Date(), i);
      months.push(format(monthDate, 'yyyy-MM'));
    }

    const monthlyData = months.map(month => ({
      month: format(parseISO(`${month}-01`), 'MMM yyyy'),
      amount: monthlySpending[month] || 0,
    }));

    // Year-over-year comparison (if we have previous year data)
    const currentYear = getYear(new Date());
    const lastYear = currentYear - 1;
    const thisYearSpending = transactions
      .filter((t) => {
        try {
          const dateStr = typeof t.transaction_date === 'string' 
            ? t.transaction_date 
            : format(new Date(t.transaction_date), 'yyyy-MM-dd');
          const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
          return getYear(date) === currentYear && typeof t.amount === 'number' && t.amount < 0;
        } catch {
          return false;
        }
      })
      .reduce((sum, t) => sum + Math.abs(t.amount), 0);

    const lastYearSpending = transactions
      .filter((t) => {
        try {
          const dateStr = typeof t.transaction_date === 'string' 
            ? t.transaction_date 
            : format(new Date(t.transaction_date), 'yyyy-MM-dd');
          const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
          return getYear(date) === lastYear && typeof t.amount === 'number' && t.amount < 0;
        } catch {
          return false;
        }
      })
      .reduce((sum, t) => sum + Math.abs(t.amount), 0);

    // Account breakdown
    const accountSpending = transactions
      .filter((t) => t && typeof t.amount === 'number' && t.amount < 0)
      .reduce((acc, t) => {
        const account = t.account_id || 'Unknown';
        acc[account] = (acc[account] || 0) + Math.abs(t.amount);
        return acc;
      }, {} as Record<string, number>);

    return {
      categorySpending: {
        labels: categoryEntries.map(([cat]) => cat),
        data: categoryEntries.map(([, amount]) => amount),
      },
      monthlySpending: {
        labels: monthlyData.map(d => d.month),
        data: monthlyData.map(d => d.amount),
      },
      accountSpending: {
        labels: Object.keys(accountSpending),
        data: Object.values(accountSpending),
      },
      yoyComparison: {
        thisYear: thisYearSpending,
        lastYear: lastYearSpending,
        change: lastYearSpending > 0 ? ((thisYearSpending - lastYearSpending) / lastYearSpending) * 100 : 0,
      },
    };
  }, [transactions]);

  // Chart options
  const textColor = isDarkMode ? '#E5E7EB' : '#374151';
  const gridColor = isDarkMode ? '#374151' : '#E5E7EB';
  
  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        backgroundColor: isDarkMode ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        titleColor: textColor,
        bodyColor: textColor,
        borderColor: gridColor,
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        ticks: { color: textColor },
        grid: { color: gridColor },
      },
      y: {
        beginAtZero: true,
        ticks: {
          color: textColor,
          callback: function(value: any) {
            return formatCurrency(value);
          },
        },
        grid: { color: gridColor },
      },
    },
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: isDarkMode ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        titleColor: textColor,
        bodyColor: textColor,
        borderColor: gridColor,
        borderWidth: 1,
        callbacks: {
          label: function(context: any) {
            return formatCurrency(context.parsed.y);
          },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: textColor },
        grid: { color: gridColor },
      },
      y: {
        beginAtZero: true,
        ticks: {
          color: textColor,
          callback: function(value: any) {
            return formatCurrency(value);
          },
        },
        grid: { color: gridColor },
      },
    },
  };

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
        labels: { color: textColor },
      },
      tooltip: {
        backgroundColor: isDarkMode ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        titleColor: textColor,
        bodyColor: textColor,
        borderColor: gridColor,
        borderWidth: 1,
        callbacks: {
          label: function(context: any) {
            const label = context.label || '';
            const value = context.parsed || 0;
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: ${formatCurrency(value)} (${percentage}%)`;
          },
        },
      },
    },
  };

  const generateColors = (count: number) => {
    const colors = [
      'rgba(99, 102, 241, 0.8)', 'rgba(239, 68, 68, 0.8)', 'rgba(34, 197, 94, 0.8)',
      'rgba(251, 146, 60, 0.8)', 'rgba(168, 85, 247, 0.8)', 'rgba(59, 130, 246, 0.8)',
      'rgba(236, 72, 153, 0.8)', 'rgba(14, 165, 233, 0.8)', 'rgba(251, 191, 36, 0.8)',
      'rgba(16, 185, 129, 0.8)',
    ];
    return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
  };

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: '📊' },
    { id: 'transactions' as TabType, label: 'Transactions', icon: '💳' },
    { id: 'ytd' as TabType, label: 'Year to Date', icon: '📅' },
    { id: 'monthly' as TabType, label: 'Monthly', icon: '📈' },
    { id: 'categories' as TabType, label: 'Categories', icon: '🏷️' },
    { id: 'housing' as TabType, label: 'Housing', icon: '🏠' },
    { id: 'trends' as TabType, label: 'Trends', icon: '📉' },
    { id: 'validation' as TabType, label: 'Data Validation', icon: '🔍' },
    { id: 'health' as TabType, label: 'API Health', icon: '🏥' },
  ];

  // Data validation and debugging info
  const dataValidation = useMemo(() => {
    if (transactions.length === 0) {
      return null;
    }

    // Get date range
    const dates = transactions
      .map(t => {
        try {
          const dateStr = typeof t.transaction_date === 'string' 
            ? t.transaction_date 
            : format(new Date(t.transaction_date), 'yyyy-MM-dd');
          return dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
        } catch {
          return null;
        }
      })
      .filter(d => d !== null) as Date[];

    const minDate = dates.length > 0 ? new Date(Math.min(...dates.map(d => d.getTime()))) : null;
    const maxDate = dates.length > 0 ? new Date(Math.max(...dates.map(d => d.getTime()))) : null;

    // Check for data issues
    const issues: string[] = [];
    const invalidDates = transactions.filter(t => {
      try {
        const dateStr = typeof t.transaction_date === 'string' 
          ? t.transaction_date 
          : format(new Date(t.transaction_date), 'yyyy-MM-dd');
        const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
        return isNaN(date.getTime());
      } catch {
        return true;
      }
    });
    if (invalidDates.length > 0) {
      issues.push(`${invalidDates.length} transactions with invalid dates`);
    }

    const invalidAmounts = transactions.filter(t => 
      typeof t.amount !== 'number' || isNaN(t.amount)
    );
    if (invalidAmounts.length > 0) {
      issues.push(`${invalidAmounts.length} transactions with invalid amounts`);
    }

    const missingDescriptions = transactions.filter(t => !t.description || t.description.trim() === '');
    if (missingDescriptions.length > 0) {
      issues.push(`${missingDescriptions.length} transactions with missing descriptions`);
    }

    // Check for duplicates
    const transactionIds = transactions.map(t => t.transaction_id);
    const duplicates = transactionIds.filter((id, index) => transactionIds.indexOf(id) !== index);
    if (duplicates.length > 0) {
      issues.push(`${duplicates.length} duplicate transaction IDs found`);
    }

    // Calculate raw totals
    const allAmounts = transactions.map(t => typeof t.amount === 'number' ? t.amount : 0);
    const rawTotal = allAmounts.reduce((sum, amt) => sum + amt, 0);
    const rawSpent = allAmounts.filter(amt => amt < 0).reduce((sum, amt) => sum + Math.abs(amt), 0);
    const rawReceived = allAmounts.filter(amt => amt > 0).reduce((sum, amt) => sum + amt, 0);

    // Sample transactions
    const sampleTransactions = transactions.slice(0, 5);

    // Breakdown by account
    const accountBreakdown = transactions.reduce((acc, t) => {
      const account = t.account_id || 'Unknown';
      if (!acc[account]) {
        acc[account] = { count: 0, total: 0, spent: 0, received: 0 };
      }
      acc[account].count++;
      const amount = typeof t.amount === 'number' ? t.amount : 0;
      acc[account].total += amount;
      if (amount < 0) {
        acc[account].spent += Math.abs(amount);
      } else {
        acc[account].received += amount;
      }
      return acc;
    }, {} as Record<string, { count: number; total: number; spent: number; received: number }>);

    return {
      totalCount: transactions.length,
      dateRange: minDate && maxDate ? {
        min: format(minDate, 'yyyy-MM-dd'),
        max: format(maxDate, 'yyyy-MM-dd'),
        minFormatted: format(minDate, 'MMM dd, yyyy'),
        maxFormatted: format(maxDate, 'MMM dd, yyyy'),
      } : null,
      rawTotals: {
        total: rawTotal,
        spent: rawSpent,
        received: rawReceived,
        net: rawReceived - rawSpent,
      },
      issues,
      sampleTransactions,
      accountBreakdown: Object.entries(accountBreakdown).map(([account, data]) => ({
        account,
        ...data,
      })),
      positiveCount: transactions.filter(t => {
        const amount = typeof t.amount === 'number' ? t.amount : 0;
        return amount > 0;
      }).length,
      negativeCount: transactions.filter(t => {
        const amount = typeof t.amount === 'number' ? t.amount : 0;
        return amount < 0;
      }).length,
      zeroCount: transactions.filter(t => {
        const amount = typeof t.amount === 'number' ? t.amount : 0;
        return amount === 0;
      }).length,
    };
  }, [transactions]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <nav className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">🏦 FinApp</h1>
              <span className="text-gray-400 dark:text-gray-500">|</span>
              <Link
                to="/import"
                className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 font-medium"
              >
                Import Transactions
              </Link>
              <span className="text-gray-400 dark:text-gray-500">|</span>
              <Link
                to="/bills"
                className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 font-medium"
              >
                Bills & Subscriptions
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Toggle dark mode"
              >
                {isDarkMode ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <span className="text-sm text-gray-700 dark:text-gray-300">{user?.email}</span>
              <Link
                to="/change-password"
                className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Change Password
              </Link>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <button
                onClick={logout}
                className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Dashboard</h2>

          {/* Tabs */}
          <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
            <nav className="-mb-px flex space-x-8 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`${
                    activeTab === tab.id
                      ? 'border-indigo-500 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6 rounded-md bg-red-50 dark:bg-red-900/20 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800 dark:text-red-400">Error loading data</h3>
                  <div className="mt-2 text-sm text-red-700 dark:text-red-300">{error}</div>
                  <div className="mt-4">
                    <div className="text-sm text-red-600 dark:text-red-400">
                      <p>Please check:</p>
                      <ul className="list-disc list-inside mt-2 space-y-1">
                        <li>Is the FastAPI backend running on port 8000?</li>
                        <li>Is PostgreSQL running and accessible?</li>
                        <li>Have you imported any transactions?</li>
                        <li>Check the browser console for more details</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab Content */}
          {loading && activeTab !== 'transactions' ? (
            <div className="text-center py-12">
              <div className="text-gray-600 dark:text-gray-400 mb-2">Loading transactions...</div>
              {loadingProgress && (
                <div className="text-sm text-gray-500 dark:text-gray-500">{loadingProgress}</div>
              )}
              <div className="mt-4 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 dark:border-indigo-400"></div>
              </div>
              <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                If this takes too long, check the browser console for errors
              </div>
            </div>
          ) : error && allTransactions.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-red-600 dark:text-red-400 mb-4">{error}</div>
              <button
                onClick={() => loadAllTransactions()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Retry
              </button>
            </div>
          ) : (
            <>
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {allTransactions.length === 0 && !loading && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                      <div className="flex">
                        <div className="flex-shrink-0">
                          <span className="text-2xl">⚠️</span>
                        </div>
                        <div className="ml-3">
                          <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-400">No transactions found</h3>
                          <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                            <p>You haven't imported any transactions yet. Go to the <Link to="/import" className="font-medium underline">Import page</Link> to upload your transaction data.</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  {/* Key Metrics Cards */}
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="flex items-center">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">💳</span>
                          </div>
                          <div className="ml-5 w-0 flex-1">
                            <dl>
                              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">YTD CC Spending</dt>
                              <dd className="text-lg font-semibold text-red-600 dark:text-red-400">
                                {formatCurrency(metrics.ytd.spent)}
                              </dd>
                            </dl>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="flex items-center">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">🏦</span>
                          </div>
                          <div className="ml-5 w-0 flex-1">
                            <dl>
                              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">YTD Checking Out</dt>
                              <dd className="text-lg font-semibold text-orange-600 dark:text-orange-400">
                                {formatCurrency(metrics.ytd.checkingOut)}
                              </dd>
                            </dl>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="flex items-center">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">📊</span>
                          </div>
                          <div className="ml-5 w-0 flex-1">
                            <dl>
                              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">This Month (CC)</dt>
                              <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                                {formatCurrency(metrics.thisMonth.spent)}
                              </dd>
                            </dl>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="flex items-center">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">📈</span>
                          </div>
                          <div className="ml-5 w-0 flex-1">
                            <dl>
                              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Daily Avg (CC)</dt>
                              <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                                {formatCurrency(metrics.monthDailyAvg)}
                              </dd>
                            </dl>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="flex items-center">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">🎯</span>
                          </div>
                          <div className="ml-5 w-0 flex-1">
                            <dl>
                              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Projected Annual</dt>
                              <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                                {formatCurrency(metrics.projectedAnnual)}
                              </dd>
                            </dl>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Insights Cards */}
                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Month-over-Month</h3>
                      <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        {metrics.momChange >= 0 ? '+' : ''}{metrics.momChange.toFixed(1)}%
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                        {metrics.momChange >= 0 ? 'Increase' : 'Decrease'} from last month
                      </p>
                      <div className="text-xs text-gray-400 dark:text-gray-500 space-y-1 border-t border-gray-200 dark:border-gray-700 pt-2 mt-2">
                        <div>This month: {formatCurrency(metrics.thisMonth.spent)}</div>
                        <div>Last month: {formatCurrency(metrics.lastMonth.spent)}</div>
                        <div className="text-gray-500 dark:text-gray-400">
                          Difference: {formatCurrency(Math.abs(metrics.thisMonth.spent - metrics.lastMonth.spent))}
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Income vs CC Spending</h3>
                      <div className={`text-3xl font-bold mb-2 ${(metrics.ytd.received - metrics.ytd.spent) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {formatCurrency(metrics.ytd.received - metrics.ytd.spent)}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Income: {formatCurrency(metrics.ytd.received)} - CC: {formatCurrency(metrics.ytd.spent)}
                      </p>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Transaction Count</h3>
                      <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        {metrics.ytd.count}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Total transactions this year</p>
                    </div>
                  </div>

                  {/* Spending vs Income Chart */}
                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Monthly Spending vs Income</h3>
                    <div className="h-80">
                      {(() => {
                        // Calculate monthly income and spending
                        const monthlyData: { [key: string]: { spending: number; income: number; checkingOut: number } } = {};
                        
                        allTransactions.forEach((t) => {
                          try {
                            const dateStr = typeof t.transaction_date === 'string' 
                              ? t.transaction_date 
                              : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                            const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                            const monthKey = format(date, 'MMM yyyy');
                            
                            if (!monthlyData[monthKey]) {
                              monthlyData[monthKey] = { spending: 0, income: 0, checkingOut: 0 };
                            }
                            
                            const amount = typeof t.amount === 'number' ? t.amount : 0;
                            
                            if (amount < 0) {
                              if (t.account_id === 'chk_main') {
                                monthlyData[monthKey].checkingOut += Math.abs(amount);
                              } else {
                                monthlyData[monthKey].spending += Math.abs(amount);
                              }
                            } else if (amount > 0 && t.account_id === 'chk_main') {
                              monthlyData[monthKey].income += amount;
                            }
                          } catch {}
                        });
                        
                        // Sort by date and take last 12 months
                        const sortedMonths = Object.keys(monthlyData)
                          .sort((a, b) => new Date(a).getTime() - new Date(b).getTime())
                          .slice(-12);
                        
                        const labels = sortedMonths;
                        const spendingData = sortedMonths.map(m => monthlyData[m]?.spending || 0);
                        const incomeData = sortedMonths.map(m => monthlyData[m]?.income || 0);
                        const checkingOutData = sortedMonths.map(m => monthlyData[m]?.checkingOut || 0);
                        
                        if (labels.length === 0) {
                          return (
                            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                              No data available
                            </div>
                          );
                        }
                        
                        return (
                          <Bar
                            data={{
                              labels,
                              datasets: [
                                {
                                  label: 'Income (Checking)',
                                  data: incomeData,
                                  backgroundColor: 'rgba(34, 197, 94, 0.8)',
                                  borderColor: 'rgba(34, 197, 94, 1)',
                                  borderWidth: 1,
                                },
                                {
                                  label: 'CC Spending',
                                  data: spendingData,
                                  backgroundColor: 'rgba(239, 68, 68, 0.8)',
                                  borderColor: 'rgba(239, 68, 68, 1)',
                                  borderWidth: 1,
                                },
                                {
                                  label: 'Checking Out',
                                  data: checkingOutData,
                                  backgroundColor: 'rgba(249, 115, 22, 0.8)',
                                  borderColor: 'rgba(249, 115, 22, 1)',
                                  borderWidth: 1,
                                },
                              ],
                            }}
                            options={{
                              ...barChartOptions,
                              plugins: {
                                ...barChartOptions.plugins,
                                legend: {
                                  display: true,
                                  position: 'top' as const,
                                  labels: {
                                    color: isDarkMode ? '#9CA3AF' : '#374151',
                                  },
                                },
                              },
                            }}
                          />
                        );
                      })()}
                    </div>
                  </div>

                  {/* Charts */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Monthly CC Spending (Last 12 Months)</h3>
                      <div className="h-64">
                        {chartData.monthlySpending.labels.length > 0 ? (
                          <Bar
                            data={{
                              labels: chartData.monthlySpending.labels,
                              datasets: [{
                                label: 'CC Spending',
                                data: chartData.monthlySpending.data,
                                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                                borderColor: 'rgba(99, 102, 241, 1)',
                                borderWidth: 1,
                              }],
                            }}
                            options={barChartOptions}
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                            No data available
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Top Categories</h3>
                      <div className="h-64">
                        {chartData.categorySpending.labels.length > 0 ? (
                          <Pie
                            data={{
                              labels: chartData.categorySpending.labels.slice(0, 8),
                              datasets: [{
                                data: chartData.categorySpending.data.slice(0, 8),
                                backgroundColor: generateColors(8),
                                borderColor: 'rgba(255, 255, 255, 1)',
                                borderWidth: 2,
                              }],
                            }}
                            options={pieChartOptions}
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                            No data available
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Transactions Tab */}
              {activeTab === 'transactions' && (
                <div className="space-y-6">
                  {/* Filters */}
                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Filters</h3>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start Date</label>
                        <input
                          type="date"
                          value={filters.start_date}
                          onChange={(e) => handleFilterChange('start_date', e.target.value)}
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">End Date</label>
                        <input
                          type="date"
                          value={filters.end_date}
                          onChange={(e) => handleFilterChange('end_date', e.target.value)}
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
                        <input
                          type="text"
                          value={filters.description}
                          onChange={(e) => handleFilterChange('description', e.target.value)}
                          placeholder="Search description"
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Category</label>
                        <input
                          type="text"
                          value={filters.category}
                          onChange={(e) => handleFilterChange('category', e.target.value)}
                          placeholder="Filter by category"
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Account</label>
                        <select
                          value={filters.account_id}
                          onChange={(e) => handleFilterChange('account_id', e.target.value)}
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        >
                          <option value="">All Accounts</option>
                          {Array.from(new Set(allTransactions.map(t => t.account_id).filter(Boolean))).sort().map(account => (
                            <option key={account} value={account}>{account}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Min Amount</label>
                        <input
                          type="number"
                          step="0.01"
                          value={filters.amount_min}
                          onChange={(e) => handleFilterChange('amount_min', e.target.value)}
                          placeholder="Min"
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max Amount</label>
                        <input
                          type="number"
                          step="0.01"
                          value={filters.amount_max}
                          onChange={(e) => handleFilterChange('amount_max', e.target.value)}
                          placeholder="Max"
                          className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Transactions Table */}
                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
                    <div className="px-4 py-5 sm:p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                        Transactions ({filteredTransactions.length})
                      </h3>
                      {error && (
                        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4 mb-4">
                          <div className="text-sm text-red-800 dark:text-red-400">{error}</div>
                        </div>
                      )}
                      {loading ? (
                        <div className="text-center py-8 text-gray-600 dark:text-gray-400">Loading transactions...</div>
                      ) : filteredTransactions.length === 0 ? (
                        <div className="text-center py-8 text-gray-500 dark:text-gray-400">No transactions found</div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                              <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Description</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Category</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Account</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Amount</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                              {filteredTransactions.map((transaction) => {
                                if (!transaction) return null;
                                const amount = typeof transaction.amount === 'number' ? transaction.amount : 0;
                                let dateStr = '';
                                try {
                                  if (transaction.transaction_date) {
                                    dateStr = format(new Date(transaction.transaction_date), 'MMM dd, yyyy');
                                  }
                                } catch (e) {
                                  dateStr = String(transaction.transaction_date || '');
                                }
                                return (
                                  <tr key={transaction.transaction_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">{dateStr || '-'}</td>
                                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">{transaction.description || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{transaction.category || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{transaction.account_id || '-'}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${amount >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                      {formatCurrency(amount)}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Year to Date Tab */}
              {activeTab === 'ytd' && (
                <div className="space-y-6">
                  {allTransactions.length === 0 && !loading && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                      <p className="text-sm text-yellow-800 dark:text-yellow-400">No transactions found. Please import some transactions first.</p>
                    </div>
                  )}
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">💳 YTD CC Spending</div>
                        <div className="mt-1 text-3xl font-semibold text-red-600 dark:text-red-400">
                          {formatCurrency(metrics.ytd.spent)}
                        </div>
                        <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                          Credit card purchases only
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">🏦 YTD Checking Out</div>
                        <div className="mt-1 text-3xl font-semibold text-orange-600 dark:text-orange-400">
                          {formatCurrency(metrics.ytd.checkingOut)}
                        </div>
                        <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                          Bills, transfers, withdrawals
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">💵 YTD Income</div>
                        <div className="mt-1 text-3xl font-semibold text-green-600 dark:text-green-400">
                          {formatCurrency(metrics.ytd.received)}
                        </div>
                        <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                          Deposits to checking
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Summary Row */}
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">💰 Net Checking Flow</div>
                        <div className={`mt-1 text-2xl font-semibold ${(metrics.ytd.received - metrics.ytd.checkingOut) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {formatCurrency(metrics.ytd.received - metrics.ytd.checkingOut)}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          Income - Checking Outflows
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">📊 Income vs CC Spending</div>
                        <div className={`mt-1 text-2xl font-semibold ${(metrics.ytd.received - metrics.ytd.spent) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {formatCurrency(metrics.ytd.received - metrics.ytd.spent)}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          Income - Credit Card Purchases
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">📈 Daily Average (CC)</div>
                        <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                          {formatCurrency(metrics.ytdDailyAvg)}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          {metrics.daysInYear} days elapsed
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                      <div className="p-5">
                        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">🎯 Projected Annual (CC)</div>
                        <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                          {formatCurrency(metrics.projectedAnnual)}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          Based on daily rate
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Explanation Card */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-blue-900 dark:text-blue-400 mb-2">💡 Understanding the Numbers</h4>
                    <div className="text-xs text-blue-800 dark:text-blue-300 space-y-1">
                      <p><strong>Net Checking Flow:</strong> Income deposits minus all checking account outflows (bills, CC payments, transfers). Shows your actual bank account cash flow.</p>
                      <p><strong>Income vs CC Spending:</strong> Income minus credit card purchases. Shows if you're charging more to cards than you earn (potential debt accumulation).</p>
                      <p className="text-blue-600 dark:text-blue-400 mt-2">⚠️ Note: Checking outflows include CC bill payments, so "Net Checking Flow" and "Income vs CC Spending" measure different things. Use "Income vs CC Spending" to see if you're overspending on credit.</p>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Year-over-Year Comparison</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">This Year</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(chartData.yoyComparison.thisYear)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Last Year</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(chartData.yoyComparison.lastYear)}</div>
                      </div>
                    </div>
                    {chartData.yoyComparison.lastYear > 0 && (
                      <div className="mt-4">
                        <div className={`text-lg font-semibold ${chartData.yoyComparison.change >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                          {chartData.yoyComparison.change >= 0 ? '+' : ''}{chartData.yoyComparison.change.toFixed(1)}% change
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {chartData.yoyComparison.change >= 0 ? 'Increase' : 'Decrease'} from last year
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Projected Annual Spending</h3>
                    <div className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
                      {formatCurrency(metrics.projectedAnnual)}
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Based on current spending rate of {formatCurrency(metrics.ytdDailyAvg)} per day
                    </p>
                  </div>
                </div>
              )}

              {/* Monthly Tab */}
              {activeTab === 'monthly' && (
                <div className="space-y-6">
                  {allTransactions.length === 0 && !loading && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                      <p className="text-sm text-yellow-800 dark:text-yellow-400">No transactions found. Please import some transactions first.</p>
                    </div>
                  )}
                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Monthly Spending (Last 12 Months)</h3>
                    <div className="h-96">
                      {chartData.monthlySpending.labels.length > 0 ? (
                        <Bar
                          data={{
                            labels: chartData.monthlySpending.labels,
                            datasets: [{
                              label: 'Spending',
                              data: chartData.monthlySpending.data,
                              backgroundColor: 'rgba(99, 102, 241, 0.8)',
                              borderColor: 'rgba(99, 102, 241, 1)',
                              borderWidth: 1,
                            }],
                          }}
                          options={barChartOptions}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                          No data available
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">💳 This Month (CC)</h3>
                      <div className="text-3xl font-bold text-red-600 dark:text-red-400 mb-2">
                        {formatCurrency(metrics.thisMonth.spent)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {metrics.daysInMonth} days elapsed
                      </div>
                      <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                        Daily average: {formatCurrency(metrics.monthDailyAvg)}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">🏦 This Month (Chk)</h3>
                      <div className="text-3xl font-bold text-orange-600 dark:text-orange-400 mb-2">
                        {formatCurrency(metrics.thisMonth.checkingOut)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Checking outflows
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">💳 Last Month (CC)</h3>
                      <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        {formatCurrency(metrics.lastMonth.spent)}
                      </div>
                      <div className="mt-4">
                        <div className={`text-lg font-semibold ${metrics.momChange >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                          {metrics.momChange >= 0 ? '+' : ''}{metrics.momChange.toFixed(1)}%
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          MoM change
                        </div>
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">🏦 Last Month (Chk)</h3>
                      <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        {formatCurrency(metrics.lastMonth.checkingOut)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Checking outflows
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Categories Tab */}
              {activeTab === 'categories' && (
                <div className="space-y-6">
                  {allTransactions.length === 0 && !loading && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                      <p className="text-sm text-yellow-800 dark:text-yellow-400">No transactions found. Please import some transactions first.</p>
                    </div>
                  )}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Spending by Category</h3>
                      <div className="h-96">
                        {chartData.categorySpending.labels.length > 0 ? (
                          <Pie
                            data={{
                              labels: chartData.categorySpending.labels,
                              datasets: [{
                                data: chartData.categorySpending.data,
                                backgroundColor: generateColors(chartData.categorySpending.labels.length),
                                borderColor: 'rgba(255, 255, 255, 1)',
                                borderWidth: 2,
                              }],
                            }}
                            options={pieChartOptions}
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                            No data available
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Top Categories</h3>
                      <div className="space-y-4">
                        {chartData.categorySpending.labels.slice(0, 10).map((category, index) => {
                          const amount = chartData.categorySpending.data[index];
                          const total = chartData.categorySpending.data.reduce((a, b) => a + b, 0);
                          const percentage = ((amount / total) * 100).toFixed(1);
                          return (
                            <div key={category} className="flex items-center justify-between">
                              <div className="flex items-center space-x-3">
                                <div className="w-4 h-4 rounded" style={{ backgroundColor: generateColors(10)[index] }}></div>
                                <span className="text-sm font-medium text-gray-900 dark:text-white">{category}</span>
                              </div>
                              <div className="text-right">
                                <div className="text-sm font-semibold text-gray-900 dark:text-white">{formatCurrency(amount)}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">{percentage}%</div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                  
                  {/* Uncategorized Transactions Section */}
                  {(() => {
                    const uncategorized = allTransactions
                      .filter(t => t && (!t.category || t.category.trim() === '') && typeof t.amount === 'number' && t.amount < 0)
                      .sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount));
                    
                    const totalUncategorized = uncategorized.reduce((sum, t) => sum + Math.abs(t.amount), 0);
                    const allSpending = allTransactions
                      .filter(t => t && typeof t.amount === 'number' && t.amount < 0)
                      .reduce((sum, t) => sum + Math.abs(t.amount), 0);
                    const uncategorizedPercent = allSpending > 0 ? ((totalUncategorized / allSpending) * 100).toFixed(1) : '0';
                    
                    // Group by description to find patterns
                    const byDescription = uncategorized.reduce((acc, t) => {
                      const desc = t.description?.trim() || 'No Description';
                      if (!acc[desc]) {
                        acc[desc] = { count: 0, total: 0, account: t.account_id || 'Unknown' };
                      }
                      acc[desc].count++;
                      acc[desc].total += Math.abs(t.amount);
                      return acc;
                    }, {} as Record<string, { count: number; total: number; account: string }>);
                    
                    const topDescriptions = Object.entries(byDescription)
                      .sort((a, b) => b[1].total - a[1].total)
                      .slice(0, 20);
                    
                    return (
                      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                        <div className="flex justify-between items-center mb-4">
                          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                            🏷️ Uncategorized Transactions
                          </h3>
                          <div className="text-right">
                            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                              {formatCurrency(totalUncategorized)}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              {uncategorized.length} transactions ({uncategorizedPercent}% of spending)
                            </div>
                          </div>
                        </div>
                        
                        {uncategorized.length === 0 ? (
                          <div className="text-center py-8 text-green-600 dark:text-green-400">
                            ✅ All transactions are categorized!
                          </div>
                        ) : (
                          <>
                            <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 mb-4">
                              <h4 className="text-sm font-medium text-orange-800 dark:text-orange-400 mb-2">
                                💡 Why are these uncategorized?
                              </h4>
                              <ul className="text-xs text-orange-700 dark:text-orange-300 space-y-1 list-disc list-inside">
                                <li>The import file may not have category data</li>
                                <li>The category column might be empty or have a different name</li>
                                <li>Bank/checking transactions often don't include categories</li>
                              </ul>
                            </div>
                            
                            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                              Top Uncategorized by Description (grouped)
                            </h4>
                            <div className="overflow-x-auto max-h-96">
                              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
                                  <tr>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Description</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Account</th>
                                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Count</th>
                                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Total</th>
                                  </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                  {topDescriptions.map(([desc, data], idx) => (
                                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                      <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">{desc}</td>
                                      <td className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">{data.account}</td>
                                      <td className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 text-right">{data.count}</td>
                                      <td className="px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 text-right">{formatCurrency(data.total)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            
                            {uncategorized.length > 20 && (
                              <div className="mt-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                                Showing top 20 of {Object.keys(byDescription).length} unique descriptions ({uncategorized.length} total transactions)
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Housing Tab */}
              {activeTab === 'housing' && (
                <div className="space-y-6">
                  {(() => {
                    // Define housing-related keywords for matching
                    const housingKeywords = {
                      mortgage: ['mortgage', 'house payment', 'home loan', 'principal', 'escrow'],
                      utilities: ['electric', 'electricity', 'power', 'gas', 'water', 'sewer', 'trash', 'garbage', 'waste'],
                      internet: ['internet', 'cable', 'comcast', 'xfinity', 'spectrum', 'att', 'at&t', 'verizon fios', 'frontier'],
                      insurance: ['home insurance', 'homeowner', 'property insurance', 'hazard insurance'],
                      hoa: ['hoa', 'homeowner association', 'condo fee', 'maintenance fee'],
                      maintenance: ['home depot', 'lowes', 'lowe\'s', 'menards', 'ace hardware', 'plumber', 'electrician', 'hvac', 'repair'],
                      property_tax: ['property tax', 'real estate tax', 'county tax'],
                    };
                    
                    const allKeywords = Object.values(housingKeywords).flat();
                    
                    // Filter housing-related transactions
                    const housingTransactions = allTransactions.filter(t => {
                      if (!t || typeof t.amount !== 'number' || t.amount >= 0) return false;
                      const desc = (t.description || '').toLowerCase();
                      const cat = (t.category || '').toLowerCase();
                      return allKeywords.some(keyword => 
                        desc.includes(keyword.toLowerCase()) || cat.includes(keyword.toLowerCase())
                      );
                    });
                    
                    // Group by category type
                    const categorized = {
                      mortgage: [] as Transaction[],
                      utilities: [] as Transaction[],
                      internet: [] as Transaction[],
                      insurance: [] as Transaction[],
                      hoa: [] as Transaction[],
                      maintenance: [] as Transaction[],
                      property_tax: [] as Transaction[],
                      other: [] as Transaction[],
                    };
                    
                    housingTransactions.forEach(t => {
                      const desc = (t.description || '').toLowerCase();
                      const cat = (t.category || '').toLowerCase();
                      const text = desc + ' ' + cat;
                      
                      let matched = false;
                      for (const [category, keywords] of Object.entries(housingKeywords)) {
                        if (keywords.some(k => text.includes(k.toLowerCase()))) {
                          categorized[category as keyof typeof categorized].push(t);
                          matched = true;
                          break;
                        }
                      }
                      if (!matched) {
                        categorized.other.push(t);
                      }
                    });
                    
                    // Calculate totals
                    const totals = Object.entries(categorized).map(([category, txns]) => ({
                      category,
                      label: category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' '),
                      count: txns.length,
                      total: txns.reduce((sum, t) => sum + Math.abs(t.amount), 0),
                      transactions: txns,
                    })).filter(c => c.count > 0);
                    
                    const grandTotal = totals.reduce((sum, c) => sum + c.total, 0);
                    
                    // Calculate monthly averages (YTD)
                    const now = new Date();
                    const startOfYear = new Date(now.getFullYear(), 0, 1);
                    const monthsElapsed = Math.max(1, (now.getMonth() + 1));
                    
                    const ytdHousing = housingTransactions.filter(t => {
                      try {
                        const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                        const txDate = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                        return txDate >= startOfYear;
                      } catch {
                        return false;
                      }
                    });
                    
                    const ytdTotal = ytdHousing.reduce((sum, t) => sum + Math.abs(t.amount), 0);
                    const monthlyAvg = ytdTotal / monthsElapsed;
                    const projectedAnnual = monthlyAvg * 12;
                    
                    // Get monthly breakdown for chart
                    const monthlyBreakdown: Record<string, Record<string, number>> = {};
                    const months: string[] = [];
                    for (let i = 11; i >= 0; i--) {
                      const monthDate = subMonths(new Date(), i);
                      const monthKey = format(monthDate, 'yyyy-MM');
                      months.push(monthKey);
                      monthlyBreakdown[monthKey] = {};
                    }
                    
                    housingTransactions.forEach(t => {
                      try {
                        const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                        const txDate = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                        const monthKey = format(txDate, 'yyyy-MM');
                        if (monthlyBreakdown[monthKey]) {
                          const desc = (t.description || '').toLowerCase();
                          const cat = (t.category || '').toLowerCase();
                          const text = desc + ' ' + cat;
                          
                          for (const [category, keywords] of Object.entries(housingKeywords)) {
                            if (keywords.some(k => text.includes(k.toLowerCase()))) {
                              monthlyBreakdown[monthKey][category] = (monthlyBreakdown[monthKey][category] || 0) + Math.abs(t.amount);
                              break;
                            }
                          }
                        }
                      } catch {
                        // Skip invalid dates
                      }
                    });
                    
                    const categoryColors: Record<string, string> = {
                      mortgage: 'rgba(220, 38, 38, 0.8)',      // Red
                      utilities: 'rgba(234, 179, 8, 0.8)',     // Yellow
                      internet: 'rgba(59, 130, 246, 0.8)',     // Blue
                      insurance: 'rgba(139, 92, 246, 0.8)',    // Purple
                      hoa: 'rgba(236, 72, 153, 0.8)',          // Pink
                      maintenance: 'rgba(249, 115, 22, 0.8)',  // Orange
                      property_tax: 'rgba(20, 184, 166, 0.8)', // Teal
                    };
                    
                    return (
                      <>
                        {housingTransactions.length === 0 ? (
                          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                            <h3 className="text-lg font-medium text-yellow-800 dark:text-yellow-400 mb-2">No Housing Transactions Found</h3>
                            <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-4">
                              We couldn't find any transactions matching common housing-related keywords.
                            </p>
                            <div className="text-xs text-yellow-600 dark:text-yellow-400">
                              <p className="font-medium mb-1">Keywords we search for:</p>
                              <ul className="list-disc list-inside space-y-1">
                                <li><strong>Mortgage:</strong> {housingKeywords.mortgage.join(', ')}</li>
                                <li><strong>Utilities:</strong> {housingKeywords.utilities.join(', ')}</li>
                                <li><strong>Internet/Cable:</strong> {housingKeywords.internet.join(', ')}</li>
                                <li><strong>Insurance:</strong> {housingKeywords.insurance.join(', ')}</li>
                                <li><strong>HOA:</strong> {housingKeywords.hoa.join(', ')}</li>
                                <li><strong>Maintenance:</strong> {housingKeywords.maintenance.join(', ')}</li>
                                <li><strong>Property Tax:</strong> {housingKeywords.property_tax.join(', ')}</li>
                              </ul>
                            </div>
                          </div>
                        ) : (
                          <>
                            {/* Summary Cards */}
                            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                              <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                                <div className="p-5">
                                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">🏠 Total Housing (All Time)</div>
                                  <div className="mt-1 text-2xl font-semibold text-red-600 dark:text-red-400">
                                    {formatCurrency(grandTotal)}
                                  </div>
                                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                    {housingTransactions.length} transactions
                                  </div>
                                </div>
                              </div>
                              <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                                <div className="p-5">
                                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">📅 YTD Housing</div>
                                  <div className="mt-1 text-2xl font-semibold text-red-600 dark:text-red-400">
                                    {formatCurrency(ytdTotal)}
                                  </div>
                                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                    {ytdHousing.length} transactions
                                  </div>
                                </div>
                              </div>
                              <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                                <div className="p-5">
                                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">📊 Monthly Average</div>
                                  <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                                    {formatCurrency(monthlyAvg)}
                                  </div>
                                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                    Based on {monthsElapsed} months
                                  </div>
                                </div>
                              </div>
                              <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                                <div className="p-5">
                                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">🎯 Projected Annual</div>
                                  <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                                    {formatCurrency(projectedAnnual)}
                                  </div>
                                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                    At current rate
                                  </div>
                                </div>
                              </div>
                            </div>
                            
                            {/* Category Breakdown */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                              <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Housing Breakdown</h3>
                                <div className="h-80">
                                  <Pie
                                    data={{
                                      labels: totals.map(c => c.label),
                                      datasets: [{
                                        data: totals.map(c => c.total),
                                        backgroundColor: totals.map(c => categoryColors[c.category] || 'rgba(156, 163, 175, 0.8)'),
                                        borderColor: 'rgba(255, 255, 255, 1)',
                                        borderWidth: 2,
                                      }],
                                    }}
                                    options={pieChartOptions}
                                  />
                                </div>
                              </div>
                              
                              <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Cost by Category</h3>
                                <div className="space-y-3">
                                  {totals.sort((a, b) => b.total - a.total).map((cat) => {
                                    const percentage = ((cat.total / grandTotal) * 100).toFixed(1);
                                    return (
                                      <div key={cat.category} className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                          <div className="w-4 h-4 rounded" style={{ backgroundColor: categoryColors[cat.category] || 'rgba(156, 163, 175, 0.8)' }}></div>
                                          <span className="text-sm font-medium text-gray-900 dark:text-white">{cat.label}</span>
                                        </div>
                                        <div className="text-right">
                                          <div className="text-sm font-semibold text-gray-900 dark:text-white">{formatCurrency(cat.total)}</div>
                                          <div className="text-xs text-gray-500 dark:text-gray-400">{cat.count} txns · {percentage}%</div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                            
                            {/* Monthly Stacked Chart */}
                            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Monthly Housing Costs (Last 12 Months)</h3>
                              <div className="h-80">
                                <Bar
                                  data={{
                                    labels: months.map(m => format(parseISO(`${m}-01`), 'MMM yyyy')),
                                    datasets: Object.entries(housingKeywords).map(([category]) => ({
                                      label: category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' '),
                                      data: months.map(m => monthlyBreakdown[m][category] || 0),
                                      backgroundColor: categoryColors[category] || 'rgba(156, 163, 175, 0.8)',
                                      borderRadius: 4,
                                    })),
                                  }}
                                  options={{
                                    ...barChartOptions,
                                    scales: {
                                      ...barChartOptions.scales,
                                      x: {
                                        ...barChartOptions.scales?.x,
                                        stacked: true,
                                      },
                                      y: {
                                        ...barChartOptions.scales?.y,
                                        stacked: true,
                                      },
                                    },
                                  }}
                                />
                              </div>
                            </div>
                            
                            {/* Transactions Table */}
                            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                                Recent Housing Transactions
                              </h3>
                              <div className="overflow-x-auto max-h-96">
                                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                  <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
                                    <tr>
                                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Date</th>
                                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Description</th>
                                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Category</th>
                                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Account</th>
                                      <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Amount</th>
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                    {housingTransactions
                                      .sort((a, b) => {
                                        try {
                                          const dateA = typeof a.transaction_date === 'string' 
                                            ? (a.transaction_date.includes('T') ? parseISO(a.transaction_date) : new Date(a.transaction_date))
                                            : new Date(a.transaction_date);
                                          const dateB = typeof b.transaction_date === 'string' 
                                            ? (b.transaction_date.includes('T') ? parseISO(b.transaction_date) : new Date(b.transaction_date))
                                            : new Date(b.transaction_date);
                                          return dateB.getTime() - dateA.getTime();
                                        } catch {
                                          return 0;
                                        }
                                      })
                                      .slice(0, 50)
                                      .map((t, idx) => (
                                        <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                          <td className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                                            {typeof t.transaction_date === 'string' ? t.transaction_date.split('T')[0] : format(new Date(t.transaction_date), 'yyyy-MM-dd')}
                                          </td>
                                          <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">{t.description}</td>
                                          <td className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">{t.category || 'Uncategorized'}</td>
                                          <td className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">{t.account_id}</td>
                                          <td className="px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 text-right">{formatCurrency(Math.abs(t.amount))}</td>
                                        </tr>
                                      ))}
                                  </tbody>
                                </table>
                              </div>
                              {housingTransactions.length > 50 && (
                                <div className="mt-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                                  Showing 50 of {housingTransactions.length} housing transactions
                                </div>
                              )}
                            </div>
                            
                            {/* Keywords Info */}
                            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                              <h4 className="text-sm font-medium text-blue-900 dark:text-blue-400 mb-2">💡 How We Identify Housing Transactions</h4>
                              <div className="text-xs text-blue-800 dark:text-blue-300 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                <div><strong>Mortgage:</strong> {housingKeywords.mortgage.join(', ')}</div>
                                <div><strong>Utilities:</strong> {housingKeywords.utilities.join(', ')}</div>
                                <div><strong>Internet/Cable:</strong> {housingKeywords.internet.join(', ')}</div>
                                <div><strong>Insurance:</strong> {housingKeywords.insurance.join(', ')}</div>
                                <div><strong>HOA:</strong> {housingKeywords.hoa.join(', ')}</div>
                                <div><strong>Maintenance:</strong> {housingKeywords.maintenance.join(', ')}</div>
                                <div><strong>Property Tax:</strong> {housingKeywords.property_tax.join(', ')}</div>
                              </div>
                              <p className="mt-2 text-xs text-blue-600 dark:text-blue-400">
                                Transactions are matched by searching description and category fields for these keywords.
                              </p>
                            </div>
                          </>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              {/* Trends Tab */}
              {activeTab === 'trends' && (
                <div className="space-y-6">
                  {allTransactions.length === 0 && !loading && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                      <p className="text-sm text-yellow-800 dark:text-yellow-400">No transactions found. Please import some transactions first.</p>
                    </div>
                  )}
                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Spending Trends (Last 12 Months)</h3>
                    <div className="h-96">
                      {chartData.monthlySpending.labels.length > 0 ? (
                        <Line
                          data={{
                            labels: chartData.monthlySpending.labels,
                            datasets: [{
                              label: 'Spending',
                              data: chartData.monthlySpending.data,
                              borderColor: 'rgba(239, 68, 68, 1)',
                              backgroundColor: 'rgba(239, 68, 68, 0.1)',
                              fill: true,
                              tension: 0.4,
                            }],
                          }}
                          options={lineChartOptions}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                          No data available
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Last 90 Days</h3>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {formatCurrency(metrics.last90Days.spent)}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Average per Month</h3>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {formatCurrency(metrics.last90Days.spent / 3)}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Trend Direction</h3>
                      <div className={`text-2xl font-bold ${metrics.momChange >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                        {metrics.momChange >= 0 ? '📈 Increasing' : '📉 Decreasing'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Data Validation Tab */}
              {activeTab === 'validation' && (
                <div className="space-y-6">
                  {!dataValidation ? (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                      <p className="text-sm text-yellow-800 dark:text-yellow-400">No transactions loaded. Please import some transactions first.</p>
                    </div>
                  ) : (
                    <>
                      {/* Spending Analysis - Detailed Diagnostics */}
                      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
                        <h3 className="text-lg font-medium text-blue-900 dark:text-blue-400 mb-4">🔍 Spending Analysis & Diagnostics</h3>
                        {(() => {
                          const now = new Date();
                          const monthStart = startOfMonth(now);
                          const monthEnd = endOfMonth(now);
                          
                          // Get this month's transactions with detailed analysis
                          const thisMonthTxs = transactions.filter(t => {
                            try {
                              const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                              const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                              return date >= monthStart && date <= monthEnd;
                            } catch { return false; }
                          });
                          
                          const expenses = thisMonthTxs.filter(t => typeof t.amount === 'number' && t.amount < 0);
                          const income = thisMonthTxs.filter(t => typeof t.amount === 'number' && t.amount > 0);
                          const zeroAmount = thisMonthTxs.filter(t => typeof t.amount === 'number' && t.amount === 0);
                          
                          // Check for duplicates
                          const transactionIds = thisMonthTxs.map(t => t.transaction_id);
                          const duplicateIds = transactionIds.filter((id, index) => transactionIds.indexOf(id) !== index);
                          const uniqueDuplicates = new Set(duplicateIds);
                          
                          // Check for transactions with same description/amount/date (potential duplicates)
                          const potentialDuplicates: { [key: string]: Transaction[] } = {};
                          thisMonthTxs.forEach(t => {
                            const key = `${t.description}_${t.amount}_${t.transaction_date}`;
                            if (!potentialDuplicates[key]) {
                              potentialDuplicates[key] = [];
                            }
                            potentialDuplicates[key].push(t);
                          });
                          const exactDuplicates = Object.values(potentialDuplicates).filter(arr => arr.length > 1);
                          
                          // Amount distribution
                          const expenseAmounts = expenses.map(t => Math.abs(typeof t.amount === 'number' ? t.amount : 0));
                          const totalExpenses = expenseAmounts.reduce((sum, amt) => sum + amt, 0);
                          const avgExpense = expenses.length > 0 ? totalExpenses / expenses.length : 0;
                          const maxExpense = expenseAmounts.length > 0 ? Math.max(...expenseAmounts) : 0;
                          const minExpense = expenseAmounts.length > 0 ? Math.min(...expenseAmounts) : 0;
                          
                          // Check date range issues
                          const dates = thisMonthTxs.map(t => {
                            try {
                              const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                              return dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                            } catch { return null; }
                          }).filter(d => d !== null) as Date[];
                          
                          const datesOutsideMonth = dates.filter(d => d < monthStart || d > monthEnd);
                          
                          return (
                            <div className="space-y-4 text-sm">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                  <div className="text-blue-800 dark:text-blue-300 font-medium mb-2">Transaction Counts:</div>
                                  <div className="space-y-1 text-blue-700 dark:text-blue-400">
                                    <div>Total this month: {thisMonthTxs.length}</div>
                                    <div>Expenses (negative): {expenses.length}</div>
                                    <div>Income (positive): {income.length}</div>
                                    <div>Zero amount: {zeroAmount.length}</div>
                                  </div>
                                </div>
                                <div>
                                  <div className="text-blue-800 dark:text-blue-300 font-medium mb-2">Amount Statistics:</div>
                                  <div className="space-y-1 text-blue-700 dark:text-blue-400">
                                    <div>Total expenses: {formatCurrency(totalExpenses)}</div>
                                    <div>Average expense: {formatCurrency(avgExpense)}</div>
                                    <div>Largest expense: {formatCurrency(maxExpense)}</div>
                                    <div>Smallest expense: {formatCurrency(minExpense)}</div>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Issues Found */}
                              <div className="mt-4">
                                <div className="text-blue-800 dark:text-blue-300 font-medium mb-2">⚠️ Potential Issues:</div>
                                <div className="space-y-2">
                                  {uniqueDuplicates.size > 0 && (
                                    <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded">
                                      <div className="font-semibold text-red-800 dark:text-red-400">Duplicate Transaction IDs: {uniqueDuplicates.size}</div>
                                      <div className="text-xs text-red-700 dark:text-red-300 mt-1">
                                        These transaction IDs appear multiple times: {Array.from(uniqueDuplicates).slice(0, 5).join(', ')}
                                        {uniqueDuplicates.size > 5 && ` ... and ${uniqueDuplicates.size - 5} more`}
                                      </div>
                                    </div>
                                  )}
                                  
                                  {exactDuplicates.length > 0 && (
                                    <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded">
                                      <div className="font-semibold text-yellow-800 dark:text-yellow-400">Potential Duplicate Transactions: {exactDuplicates.length} groups</div>
                                      <div className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
                                        Transactions with identical description, amount, and date (may be legitimate duplicates)
                                      </div>
                                    </div>
                                  )}
                                  
                                  {datesOutsideMonth.length > 0 && (
                                    <div className="bg-orange-50 dark:bg-orange-900/20 p-3 rounded">
                                      <div className="font-semibold text-orange-800 dark:text-orange-400">Date Range Issue: {datesOutsideMonth.length} transactions</div>
                                      <div className="text-xs text-orange-700 dark:text-orange-300 mt-1">
                                        Some transactions have dates outside the current month range
                                      </div>
                                    </div>
                                  )}
                                  
                                  {avgExpense > 500 && (
                                    <div className="bg-purple-50 dark:bg-purple-900/20 p-3 rounded">
                                      <div className="font-semibold text-purple-800 dark:text-purple-400">High Average Expense: {formatCurrency(avgExpense)}</div>
                                      <div className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                                        Average expense per transaction seems unusually high. Check for:
                                        <ul className="list-disc list-inside mt-1">
                                          <li>Duplicate transactions being counted</li>
                                          <li>Amount sign errors (positive instead of negative)</li>
                                          <li>Transactions from wrong date range</li>
                                        </ul>
                                      </div>
                                    </div>
                                  )}
                                  
                                  {expenses.length > 0 && totalExpenses / expenses.length > 1000 && (
                                    <div className="bg-pink-50 dark:bg-pink-900/20 p-3 rounded">
                                      <div className="font-semibold text-pink-800 dark:text-pink-400">Very High Spending Detected</div>
                                      <div className="text-xs text-pink-700 dark:text-pink-300 mt-1">
                                        Average of {formatCurrency(totalExpenses / expenses.length)} per expense transaction. 
                                        This suggests possible data issues. Check the "Top Expenses" table below.
                                      </div>
                                    </div>
                                  )}
                                  
                                  {uniqueDuplicates.size === 0 && exactDuplicates.length === 0 && datesOutsideMonth.length === 0 && avgExpense <= 500 && (
                                    <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded">
                                      <div className="text-green-800 dark:text-green-400">✅ No obvious data quality issues detected</div>
                                    </div>
                                  )}
                                </div>
                              </div>
                              
                              {/* Date Range Verification */}
                              <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded">
                                <div className="text-blue-800 dark:text-blue-300 font-medium mb-2">Date Range Verification:</div>
                                <div className="text-xs text-gray-700 dark:text-gray-300 space-y-1">
                                  <div>Month range: {format(monthStart, 'MMM dd, yyyy')} to {format(monthEnd, 'MMM dd, yyyy')}</div>
                                  <div>Transactions found in this range: {thisMonthTxs.length}</div>
                                  {(() => {
                                    const dateCounts: { [key: string]: number } = {};
                                    thisMonthTxs.forEach(t => {
                                      try {
                                        const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                                        const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                                        const monthKey = format(date, 'yyyy-MM');
                                        dateCounts[monthKey] = (dateCounts[monthKey] || 0) + 1;
                                      } catch {}
                                    });
                                    const otherMonths = Object.entries(dateCounts).filter(([month]) => month !== format(monthStart, 'yyyy-MM'));
                                    if (otherMonths.length > 0) {
                                      return (
                                        <div className="text-red-600 dark:text-red-400 mt-2">
                                          ⚠️ Found transactions from other months: {otherMonths.map(([month, count]) => `${month} (${count})`).join(', ')}
                                        </div>
                                      );
                                    }
                                    return null;
                                  })()}
                                </div>
                              </div>
                              
                              {/* Amount Sign Analysis */}
                              <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded">
                                <div className="text-blue-800 dark:text-blue-300 font-medium mb-2">Amount Sign Analysis:</div>
                                <div className="text-xs text-gray-700 dark:text-gray-300 space-y-1">
                                  <div>Expected: Expenses should be NEGATIVE, Income should be POSITIVE</div>
                                  <div>If you see expenses as POSITIVE, the import may have a sign error</div>
                                  <div>Check sample transactions below to verify amount signs</div>
                                </div>
                              </div>
                            </div>
                          );
                        })()}
                      </div>

                      {/* Duplicate Analysis */}
                      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
                        <h3 className="text-lg font-medium text-red-900 dark:text-red-400 mb-4">🔄 Duplicate Analysis</h3>
                        {(() => {
                          // Check for duplicate transaction IDs (should never happen)
                          const idCounts: { [key: string]: number } = {};
                          allTransactions.forEach(t => {
                            idCounts[t.transaction_id] = (idCounts[t.transaction_id] || 0) + 1;
                          });
                          const duplicateIds = Object.entries(idCounts).filter(([_, count]) => count > 1);
                          
                          // Check for potential duplicates (same description, amount, date, account)
                          const txnKeys: { [key: string]: Transaction[] } = {};
                          allTransactions.forEach(t => {
                            const dateStr = typeof t.transaction_date === 'string' 
                              ? t.transaction_date.split('T')[0] 
                              : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                            const key = `${dateStr}|${t.description}|${t.amount}|${t.account_id}`;
                            if (!txnKeys[key]) {
                              txnKeys[key] = [];
                            }
                            txnKeys[key].push(t);
                          });
                          const potentialDuplicateGroups = Object.entries(txnKeys).filter(([_, txns]) => txns.length > 1);
                          
                          // Calculate duplicate amounts
                          let duplicateSpending = 0;
                          potentialDuplicateGroups.forEach(([_, txns]) => {
                            // Count extra transactions beyond the first
                            txns.slice(1).forEach(t => {
                              const amt = typeof t.amount === 'number' ? t.amount : 0;
                              if (amt < 0) {
                                duplicateSpending += Math.abs(amt);
                              }
                            });
                          });
                          
                          return (
                            <div className="space-y-4">
                              {/* Summary */}
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="p-3 bg-white dark:bg-gray-800 rounded shadow">
                                  <div className="text-sm text-gray-500 dark:text-gray-400">Duplicate IDs</div>
                                  <div className={`text-2xl font-bold ${duplicateIds.length > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                    {duplicateIds.length}
                                  </div>
                                </div>
                                <div className="p-3 bg-white dark:bg-gray-800 rounded shadow">
                                  <div className="text-sm text-gray-500 dark:text-gray-400">Potential Duplicate Groups</div>
                                  <div className={`text-2xl font-bold ${potentialDuplicateGroups.length > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                                    {potentialDuplicateGroups.length}
                                  </div>
                                </div>
                                <div className="p-3 bg-white dark:bg-gray-800 rounded shadow">
                                  <div className="text-sm text-gray-500 dark:text-gray-400">Duplicate Spending Impact</div>
                                  <div className={`text-2xl font-bold ${duplicateSpending > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                    {formatCurrency(duplicateSpending)}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Explanation */}
                              <div className="text-sm text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900/30 p-3 rounded">
                                <div className="font-semibold mb-1">What this means:</div>
                                <ul className="list-disc list-inside space-y-1 text-xs">
                                  <li><strong>Duplicate IDs:</strong> Same transaction imported multiple times (data error)</li>
                                  <li><strong>Potential Duplicates:</strong> Different transaction IDs but same date/description/amount/account (may be legitimate like subscription charges, or may be import errors)</li>
                                  <li><strong>Duplicate Spending Impact:</strong> How much extra spending is counted if all potential duplicates are actual duplicates</li>
                                </ul>
                              </div>
                              
                              {/* Potential Duplicates Table */}
                              {potentialDuplicateGroups.length > 0 && (
                                <div>
                                  <div className="font-semibold text-red-800 dark:text-red-400 mb-2">
                                    Potential Duplicate Transactions (Top 10 groups):
                                  </div>
                                  <div className="overflow-x-auto">
                                    <table className="min-w-full text-xs">
                                      <thead>
                                        <tr className="border-b border-red-300 dark:border-red-700 bg-red-100 dark:bg-red-900/30">
                                          <th className="px-2 py-2 text-left">Date</th>
                                          <th className="px-2 py-2 text-left">Description</th>
                                          <th className="px-2 py-2 text-left">Account</th>
                                          <th className="px-2 py-2 text-right">Amount</th>
                                          <th className="px-2 py-2 text-center">Count</th>
                                          <th className="px-2 py-2 text-right">Extra $</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {potentialDuplicateGroups
                                          .sort((a, b) => {
                                            // Sort by count * amount (biggest impact first)
                                            const aAmt = Math.abs(typeof a[1][0].amount === 'number' ? a[1][0].amount : 0);
                                            const bAmt = Math.abs(typeof b[1][0].amount === 'number' ? b[1][0].amount : 0);
                                            return (b[1].length * bAmt) - (a[1].length * aAmt);
                                          })
                                          .slice(0, 10)
                                          .map(([, txns], idx) => {
                                            const first = txns[0];
                                            const amount = typeof first.amount === 'number' ? first.amount : 0;
                                            const extraAmount = Math.abs(amount) * (txns.length - 1);
                                            let dateStr = '';
                                            try {
                                              dateStr = format(new Date(first.transaction_date), 'MMM dd, yyyy');
                                            } catch {
                                              dateStr = String(first.transaction_date);
                                            }
                                            return (
                                              <tr key={idx} className="border-b border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30">
                                                <td className="px-2 py-2">{dateStr}</td>
                                                <td className="px-2 py-2">{first.description?.substring(0, 35)}...</td>
                                                <td className="px-2 py-2">{first.account_id}</td>
                                                <td className="px-2 py-2 text-right font-medium">
                                                  {formatCurrency(amount)}
                                                </td>
                                                <td className="px-2 py-2 text-center font-bold text-red-600">
                                                  {txns.length}x
                                                </td>
                                                <td className="px-2 py-2 text-right font-bold text-red-600">
                                                  {formatCurrency(extraAmount)}
                                                </td>
                                              </tr>
                                            );
                                          })}
                                      </tbody>
                                    </table>
                                  </div>
                                  <div className="text-xs text-red-600 dark:text-red-400 mt-2">
                                    * "Count" shows how many times this transaction appears. "Extra $" is the duplicate spending if all but one are duplicates.
                                  </div>
                                </div>
                              )}
                              
                              {potentialDuplicateGroups.length === 0 && duplicateIds.length === 0 && (
                                <div className="text-green-600 dark:text-green-400 font-semibold">
                                  ✅ No duplicate transactions detected
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </div>

                      {/* Amount Sign Check */}
                      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                        <h3 className="text-lg font-medium text-yellow-900 dark:text-yellow-400 mb-4">⚠️ Amount Sign Check</h3>
                        {(() => {
                          const now = new Date();
                          const monthStart = startOfMonth(now);
                          const monthEnd = endOfMonth(now);
                          
                          const thisMonthTxs = transactions.filter(t => {
                            try {
                              const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                              const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                              return date >= monthStart && date <= monthEnd;
                            } catch { return false; }
                          });
                          
                          // Check for expenses stored as positive (wrong sign)
                          const wrongSignExpenses = thisMonthTxs.filter(t => {
                            const amount = typeof t.amount === 'number' ? t.amount : 0;
                            // If it's a large positive amount, it might be an expense stored incorrectly
                            // Check common expense keywords
                            const desc = (t.description || '').toLowerCase();
                            const isLikelyExpense = desc.includes('purchase') || desc.includes('charge') || 
                                                   desc.includes('payment') || desc.includes('debit') ||
                                                   desc.includes('withdrawal') || desc.includes('fee');
                            return amount > 0 && amount > 100 && isLikelyExpense;
                          });
                          
                          if (wrongSignExpenses.length > 0) {
                            return (
                              <div>
                                <div className="text-yellow-800 dark:text-yellow-400 font-semibold mb-2">
                                  Found {wrongSignExpenses.length} transactions that might be expenses stored as POSITIVE amounts:
                                </div>
                                <div className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
                                  These should be NEGATIVE. This could double your spending if they're being counted as both income and expenses.
                                </div>
                                <div className="overflow-x-auto">
                                  <table className="min-w-full text-xs">
                                    <thead>
                                      <tr className="border-b border-yellow-300 dark:border-yellow-700">
                                        <th className="px-2 py-1 text-left">Date</th>
                                        <th className="px-2 py-1 text-left">Description</th>
                                        <th className="px-2 py-1 text-right">Amount</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {wrongSignExpenses.slice(0, 10).map(t => (
                                        <tr key={t.transaction_id} className="border-b border-yellow-200 dark:border-yellow-800">
                                          <td className="px-2 py-1">{format(new Date(t.transaction_date), 'MMM dd')}</td>
                                          <td className="px-2 py-1">{t.description?.substring(0, 40)}</td>
                                          <td className="px-2 py-1 text-right font-semibold text-red-600 dark:text-red-400">
                                            {formatCurrency(typeof t.amount === 'number' ? t.amount : 0)}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            );
                          }
                          
                          return (
                            <div className="text-yellow-800 dark:text-yellow-400">
                              ✅ Amount signs look correct (expenses are negative, income is positive)
                            </div>
                          );
                        })()}
                      </div>

                      {/* Top Expenses This Month */}
                      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Top 20 Expenses This Month</h3>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                              <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Date</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Description</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Category</th>
                                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Amount</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                              {(() => {
                                const thisMonthTxs = transactions.filter(t => {
                                  try {
                                    const dateStr = typeof t.transaction_date === 'string' ? t.transaction_date : format(new Date(t.transaction_date), 'yyyy-MM-dd');
                                    const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr);
                                    const monthStart = startOfMonth(new Date());
                                    const now = new Date();
                                    return date >= monthStart && date <= now && typeof t.amount === 'number' && t.amount < 0;
                                  } catch { return false; }
                                }).sort((a, b) => {
                                  const amtA = typeof a.amount === 'number' ? Math.abs(a.amount) : 0;
                                  const amtB = typeof b.amount === 'number' ? Math.abs(b.amount) : 0;
                                  return amtB - amtA;
                                }).slice(0, 20);
                                
                                return thisMonthTxs.map((t) => {
                                  const amount = typeof t.amount === 'number' ? t.amount : 0;
                                  let dateStr = '';
                                  try {
                                    if (t.transaction_date) {
                                      dateStr = format(new Date(t.transaction_date), 'MMM dd, yyyy');
                                    }
                                  } catch {
                                    dateStr = String(t.transaction_date || '');
                                  }
                                  return (
                                    <tr key={t.transaction_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{dateStr}</td>
                                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{t.description || '-'}</td>
                                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{t.category || '-'}</td>
                                      <td className="px-4 py-3 text-sm text-right font-medium text-red-600 dark:text-red-400">
                                        {formatCurrency(Math.abs(amount))}
                                      </td>
                                    </tr>
                                  );
                                });
                              })()}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      {/* Summary Cards */}
                      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
                        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-5">
                          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Transactions</div>
                          <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                            {dataValidation.totalCount.toLocaleString()}
                          </div>
                        </div>
                        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-5">
                          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Positive (Income)</div>
                          <div className="mt-1 text-2xl font-semibold text-green-600 dark:text-green-400">
                            {dataValidation.positiveCount.toLocaleString()}
                          </div>
                        </div>
                        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-5">
                          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Negative (Expenses)</div>
                          <div className="mt-1 text-2xl font-semibold text-red-600 dark:text-red-400">
                            {dataValidation.negativeCount.toLocaleString()}
                          </div>
                        </div>
                        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-5">
                          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Zero Amount</div>
                          <div className="mt-1 text-2xl font-semibold text-yellow-600 dark:text-yellow-400">
                            {dataValidation.zeroCount.toLocaleString()}
                          </div>
                        </div>
                      </div>

                      {/* Date Range */}
                      {dataValidation.dateRange && (
                        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Date Range</h3>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <div className="text-sm text-gray-500 dark:text-gray-400">Earliest Transaction</div>
                              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                                {dataValidation.dateRange.minFormatted}
                              </div>
                              <div className="text-xs text-gray-400 dark:text-gray-500">{dataValidation.dateRange.min}</div>
                            </div>
                            <div>
                              <div className="text-sm text-gray-500 dark:text-gray-400">Latest Transaction</div>
                              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                                {dataValidation.dateRange.maxFormatted}
                              </div>
                              <div className="text-xs text-gray-400 dark:text-gray-500">{dataValidation.dateRange.max}</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Raw Totals */}
                      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Raw Totals (All Transactions)</h3>
                        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                          <div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">Total Spent</div>
                            <div className="text-xl font-semibold text-red-600 dark:text-red-400">
                              {formatCurrency(dataValidation.rawTotals.spent)}
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">Total Received</div>
                            <div className="text-xl font-semibold text-green-600 dark:text-green-400">
                              {formatCurrency(dataValidation.rawTotals.received)}
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">Net Flow</div>
                            <div className={`text-xl font-semibold ${dataValidation.rawTotals.net >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                              {formatCurrency(dataValidation.rawTotals.net)}
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">Sum of All Amounts</div>
                            <div className={`text-xl font-semibold ${dataValidation.rawTotals.total >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                              {formatCurrency(dataValidation.rawTotals.total)}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Data Issues */}
                      {dataValidation.issues.length > 0 && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
                          <h3 className="text-lg font-medium text-red-900 dark:text-red-400 mb-4">⚠️ Data Issues Found</h3>
                          <ul className="list-disc list-inside space-y-2">
                            {dataValidation.issues.map((issue, index) => (
                              <li key={index} className="text-sm text-red-800 dark:text-red-300">{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {dataValidation.issues.length === 0 && (
                        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
                          <div className="flex items-center">
                            <span className="text-2xl mr-3">✅</span>
                            <div>
                              <h3 className="text-lg font-medium text-green-900 dark:text-green-400">Data Validation Passed</h3>
                              <p className="text-sm text-green-800 dark:text-green-300 mt-1">No data integrity issues found!</p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Account Breakdown */}
                      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Breakdown by Account</h3>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                              <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Account</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Count</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Spent</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Received</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Net</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                              {dataValidation.accountBreakdown.map((account) => (
                                <tr key={account.account} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                                    {account.account}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-400">
                                    {account.count}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600 dark:text-red-400">
                                    {formatCurrency(account.spent)}
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600 dark:text-green-400">
                                    {formatCurrency(account.received)}
                                  </td>
                                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${account.total >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {formatCurrency(account.total)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Sample Transactions */}
                      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Sample Transactions (First 5)</h3>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                              <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Description</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Category</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Account</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Amount</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                              {dataValidation.sampleTransactions.map((transaction) => {
                                const amount = typeof transaction.amount === 'number' ? transaction.amount : 0;
                                let dateStr = '';
                                try {
                                  if (transaction.transaction_date) {
                                    dateStr = format(new Date(transaction.transaction_date), 'MMM dd, yyyy');
                                  }
                                } catch (e) {
                                  dateStr = String(transaction.transaction_date || '');
                                }
                                return (
                                  <tr key={transaction.transaction_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">{dateStr || '-'}</td>
                                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">{transaction.description || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{transaction.category || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{transaction.account_id || '-'}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${amount >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                      {formatCurrency(amount)}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Comparison with Calculated Metrics */}
                      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
                        <h3 className="text-lg font-medium text-blue-900 dark:text-blue-400 mb-4">📊 Data Verification</h3>
                        <div className="space-y-3 text-sm">
                          <div className="flex justify-between">
                            <span className="text-blue-800 dark:text-blue-300">Raw Total Spent:</span>
                            <span className="font-semibold text-blue-900 dark:text-blue-200">{formatCurrency(dataValidation.rawTotals.spent)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-800 dark:text-blue-300">YTD Spent (from metrics):</span>
                            <span className="font-semibold text-blue-900 dark:text-blue-200">{formatCurrency(metrics.ytd.spent)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-800 dark:text-blue-300">Difference:</span>
                            <span className={`font-semibold ${Math.abs(dataValidation.rawTotals.spent - metrics.ytd.spent) < 0.01 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                              {formatCurrency(Math.abs(dataValidation.rawTotals.spent - metrics.ytd.spent))}
                            </span>
                          </div>
                          <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-700">
                            <p className="text-xs text-blue-700 dark:text-blue-300">
                              <strong>Note:</strong> Raw totals include ALL transactions in the loaded dataset. 
                              YTD metrics only include transactions from the current year. 
                              If dates are outside the year range, there will be a difference.
                            </p>
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Health Check Tab */}
              {activeTab === 'health' && (
                <div className="space-y-6">
                  {/* Refresh Button */}
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">API Health Status</h2>
                      {healthData.lastChecked && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Last checked: {format(healthData.lastChecked, 'MMM dd, yyyy HH:mm:ss')}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={async () => {
                        setHealthData(prev => ({ ...prev, healthLoading: true, healthError: '' }));
                        try {
                          const [health, readiness] = await Promise.all([
                            healthApi.getHealth(),
                            healthApi.getReadiness(),
                          ]);
                          setHealthData({
                            health,
                            readiness,
                            healthLoading: false,
                            healthError: '',
                            lastChecked: new Date(),
                          });
                        } catch (err: any) {
                          setHealthData(prev => ({
                            ...prev,
                            healthLoading: false,
                            healthError: err.message || 'Failed to fetch health status',
                            lastChecked: new Date(),
                          }));
                        }
                      }}
                      disabled={healthData.healthLoading}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {healthData.healthLoading ? 'Checking...' : '🔄 Refresh'}
                    </button>
                  </div>

                  {healthData.healthError && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                      <div className="text-red-800 dark:text-red-400 font-semibold">Error checking health</div>
                      <div className="text-sm text-red-700 dark:text-red-300">{healthData.healthError}</div>
                    </div>
                  )}

                  {/* Overall Status */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Basic Health */}
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Basic Health Check</h3>
                      {healthData.health ? (
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Status</span>
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              healthData.health.status === 'healthy' 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            }`}>
                              {healthData.health.status === 'healthy' ? '✅ Healthy' : '❌ Unhealthy'}
                            </span>
                          </div>
                          {healthData.health.service && (
                            <div className="flex items-center justify-between">
                              <span className="text-gray-600 dark:text-gray-400">Service</span>
                              <span className="text-gray-900 dark:text-white">{healthData.health.service}</span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <p className="text-gray-500 dark:text-gray-400 mb-4">Click "Refresh" to check API health</p>
                        </div>
                      )}
                    </div>

                    {/* Readiness Check */}
                    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Readiness Check</h3>
                      {healthData.readiness ? (
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Overall Status</span>
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              healthData.readiness.status === 'ready' 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            }`}>
                              {healthData.readiness.status === 'ready' ? '✅ Ready' : '❌ Not Ready'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Database</span>
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              healthData.readiness.database === 'connected' 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            }`}>
                              {healthData.readiness.database === 'connected' ? '✅ Connected' : `❌ ${healthData.readiness.database}`}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Cognito</span>
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              healthData.readiness.cognito === 'connected' 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            }`}>
                              {healthData.readiness.cognito === 'connected' ? '✅ Connected' : `❌ ${healthData.readiness.cognito}`}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <p className="text-gray-500 dark:text-gray-400 mb-4">Click "Refresh" to check readiness</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Connection Details */}
                  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">API Connection Details</h3>
                    <div className="space-y-3 text-sm">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">API Base URL:</span>
                          <div className="font-mono text-gray-900 dark:text-white mt-1 p-2 bg-gray-100 dark:bg-gray-700 rounded">
                            {window.location.origin}/api/v1
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Authentication:</span>
                          <div className="font-mono text-gray-900 dark:text-white mt-1 p-2 bg-gray-100 dark:bg-gray-700 rounded">
                            {user ? '✅ Authenticated' : '❌ Not authenticated'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Troubleshooting Tips */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
                    <h3 className="text-lg font-medium text-blue-900 dark:text-blue-400 mb-4">💡 Troubleshooting Tips</h3>
                    <div className="space-y-3 text-sm text-blue-800 dark:text-blue-300">
                      <div>
                        <strong>If Database is not connected:</strong>
                        <ul className="list-disc list-inside mt-1 text-xs">
                          <li>Ensure PostgreSQL is running</li>
                          <li>Check DATABASE_URL in api/.env</li>
                          <li>Run migrations: <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">alembic upgrade head</code></li>
                        </ul>
                      </div>
                      <div>
                        <strong>If Cognito is not connected:</strong>
                        <ul className="list-disc list-inside mt-1 text-xs">
                          <li>Check AWS credentials are configured</li>
                          <li>Verify COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID in api/.env</li>
                          <li>Ensure the Cognito user pool exists in the correct region</li>
                        </ul>
                      </div>
                      <div>
                        <strong>If API is not responding:</strong>
                        <ul className="list-disc list-inside mt-1 text-xs">
                          <li>Ensure the API is running: <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">uvicorn api.main:app --reload</code></li>
                          <li>Check terminal for error messages</li>
                          <li>Verify Vite proxy configuration in vite.config.ts</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

