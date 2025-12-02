import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { SparklesIcon, ShieldCheckIcon, BoltIcon, ClockIcon } from '@heroicons/react/24/outline';

export default function Login() {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(formData.email, formData.password);
      navigate('/');
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Invalid credentials. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-navy-950">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-navy-900 via-navy-900 to-tronas-950 p-12 flex-col justify-between relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-grid-pattern opacity-30" />

        {/* Animated Glow Orbs */}
        <div className="absolute top-20 left-20 w-64 h-64 bg-tronas-500/20 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-40 right-20 w-96 h-96 bg-tronas-600/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-tronas-400 to-tronas-600 flex items-center justify-center shadow-glow">
                <SparklesIcon className="w-8 h-8 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-tronas-400 rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">Tronas</h1>
              <p className="text-sm text-tronas-400 uppercase tracking-wider">PIA Automation</p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-4xl font-bold text-white leading-tight">
              Intelligent Document<br />
              Processing for<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-tronas-400 to-tronas-300">
                Public Records
              </span>
            </h2>
            <p className="mt-6 text-lg text-navy-300 max-w-md">
              AI-powered automation for Texas Public Information Act compliance.
              Process thousands of documents in minutes, not weeks.
            </p>
          </div>

          {/* Features */}
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 rounded-xl bg-navy-800/50 border border-navy-700 backdrop-blur-sm">
              <div className="p-2 rounded-lg bg-tronas-500/20">
                <BoltIcon className="w-6 h-6 text-tronas-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">AI Classification</h3>
                <p className="text-sm text-navy-400">85%+ accuracy on document responsiveness</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 rounded-xl bg-navy-800/50 border border-navy-700 backdrop-blur-sm">
              <div className="p-2 rounded-lg bg-tronas-500/20">
                <ClockIcon className="w-6 h-6 text-tronas-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">60-70% Time Savings</h3>
                <p className="text-sm text-navy-400">Reduce manual review hours significantly</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 rounded-xl bg-navy-800/50 border border-navy-700 backdrop-blur-sm">
              <div className="p-2 rounded-lg bg-tronas-500/20">
                <ShieldCheckIcon className="w-6 h-6 text-tronas-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Texas PIA Compliant</h3>
                <p className="text-sm text-navy-400">Built-in deadline tracking & exemptions</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10">
          <p className="text-navy-500 text-sm">
            City of San Antonio • Document Intelligence Platform
          </p>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-navy-950">
        <div className="w-full max-w-md space-y-8 animate-slide-up">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center">
            <div className="flex justify-center mb-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-tronas-400 to-tronas-600 flex items-center justify-center shadow-glow">
                  <SparklesIcon className="w-10 h-10 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-tronas-400 rounded-full animate-pulse" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-white">Tronas</h1>
            <p className="text-tronas-400 text-sm">PIA Automation Platform</p>
          </div>

          {/* Login Card */}
          <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-8 shadow-xl">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white">Welcome back</h2>
              <p className="text-navy-400 mt-2">Sign in to your account to continue</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-danger-500/10 border border-danger-500/30 rounded-xl p-4 text-danger-400 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                  placeholder="your.email@sanantonio.gov"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                  placeholder="Enter your password"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border-navy-600 bg-navy-800 text-tronas-500 focus:ring-tronas-500/50"
                  />
                  <span className="ml-2 text-sm text-navy-400">Remember me</span>
                </label>
                <a href="#" className="text-sm text-tronas-400 hover:text-tronas-300 transition-colors">
                  Forgot password?
                </a>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full px-4 py-3 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white rounded-xl font-medium shadow-glow transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Signing in...
                  </span>
                ) : 'Sign In'}
              </button>
            </form>

            {/* Azure AD Sign In */}
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-navy-700" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-navy-900/50 text-navy-500">or continue with</span>
                </div>
              </div>

              <button
                type="button"
                className="mt-4 w-full flex items-center justify-center gap-3 px-4 py-3 border border-navy-700 rounded-xl text-navy-300 hover:bg-navy-800/50 hover:text-white hover:border-navy-600 transition-all"
              >
                <svg className="w-5 h-5" viewBox="0 0 21 21">
                  <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
                  <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
                  <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
                  <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
                </svg>
                Sign in with Microsoft
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center text-navy-500 text-sm">
            <p>Powered by Azure Document Intelligence</p>
            <p className="mt-1">Secure • Compliant • Intelligent</p>
          </div>
        </div>
      </div>
    </div>
  );
}
