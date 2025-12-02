import { useState } from 'react';
import { supabase } from '../lib/supabase';

type AuthMethod = 'email' | 'magic-link';
type AuthMode = 'signin' | 'signup';

export function Login() {
  const [method, setMethod] = useState<AuthMethod>('email');
  const [mode, setMode] = useState<AuthMode>('signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    if (mode === 'signup') {
      const { error, data } = await supabase.auth.signUp({ email, password });
      if (error) {
        setMessage(error.message);
      } else if (data.user?.identities?.length === 0) {
        setMessage('This email is already registered. Try signing in instead.');
      } else {
        setMessage('Account created! Check your email to confirm, then sign in.');
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setMessage(error.message);
      }
    }
    setLoading(false);
  };

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });

    if (error) {
      setMessage(error.message);
    } else {
      setMessage('Check your email for the magic link!');
    }
    setLoading(false);
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    });
    if (error) {
      setMessage(error.message);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[var(--phronai-dark)] flex items-center justify-center p-4">
      {/* Background gradient effect */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--phronai-primary)] opacity-10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[var(--phronai-secondary)] opacity-10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative glass rounded-2xl p-8 max-w-md w-full glow animate-fade-in">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold gradient-text mb-2">PHRONAI</h1>
          <p className="text-[var(--phronai-text-muted)]">
            Operational Intelligence Agent
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex gap-2 mb-6 p-1 bg-[var(--phronai-surface)] rounded-lg">
          <button
            onClick={() => { setMode('signup'); setEmail(''); setPassword(''); setMessage(''); }}
            className={`flex-1 py-2 px-4 rounded-md transition-all ${
              mode === 'signup'
                ? 'bg-[var(--phronai-primary)] text-white'
                : 'text-[var(--phronai-text-muted)] hover:text-white'
            }`}
          >
            Sign Up
          </button>
          <button
            onClick={() => { setMode('signin'); setEmail(''); setPassword(''); setMessage(''); }}
            className={`flex-1 py-2 px-4 rounded-md transition-all ${
              mode === 'signin'
                ? 'bg-[var(--phronai-primary)] text-white'
                : 'text-[var(--phronai-text-muted)] hover:text-white'
            }`}
          >
            Sign In
          </button>
        </div>

        {/* Method Toggle */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setMethod('email')}
            className={`flex-1 py-2 px-4 rounded-lg border transition-all ${
              method === 'email'
                ? 'border-[var(--phronai-primary)] bg-[var(--phronai-surface-light)] text-white'
                : 'border-[var(--phronai-surface-light)] text-[var(--phronai-text-muted)]'
            }`}
          >
            Email & Password
          </button>
          <button
            onClick={() => setMethod('magic-link')}
            className={`flex-1 py-2 px-4 rounded-lg border transition-all ${
              method === 'magic-link'
                ? 'border-[var(--phronai-secondary)] bg-[var(--phronai-surface-light)] text-white'
                : 'border-[var(--phronai-surface-light)] text-[var(--phronai-text-muted)]'
            }`}
          >
            Magic Link
          </button>
        </div>

        {/* Email Form */}
        {method === 'email' && (
          <form onSubmit={handleEmailAuth} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--phronai-text-muted)] mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-[var(--phronai-surface)] border border-[var(--phronai-surface-light)] rounded-lg text-white placeholder-[var(--phronai-text-muted)] focus:outline-none focus:border-[var(--phronai-primary)] transition-all"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--phronai-text-muted)] mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-[var(--phronai-surface)] border border-[var(--phronai-surface-light)] rounded-lg text-white placeholder-[var(--phronai-text-muted)] focus:outline-none focus:border-[var(--phronai-primary)] transition-all"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-3"
            >
              {loading ? 'Processing...' : mode === 'signup' ? 'Create Account' : 'Sign In'}
            </button>
          </form>
        )}

        {/* Magic Link Form */}
        {method === 'magic-link' && (
          <form onSubmit={handleMagicLink} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--phronai-text-muted)] mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-[var(--phronai-surface)] border border-[var(--phronai-surface-light)] rounded-lg text-white placeholder-[var(--phronai-text-muted)] focus:outline-none focus:border-[var(--phronai-secondary)] transition-all"
                placeholder="you@example.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-full font-semibold bg-gradient-to-r from-[var(--phronai-secondary)] to-[var(--phronai-primary)] text-white hover:opacity-90 transition-all disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send Magic Link'}
            </button>
          </form>
        )}

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--phronai-surface-light)]"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-[var(--phronai-surface)] text-[var(--phronai-text-muted)] rounded">
              Or continue with
            </span>
          </div>
        </div>

        {/* Google Button */}
        <button
          onClick={handleGoogleLogin}
          disabled={loading}
          className="w-full flex items-center justify-center gap-3 bg-white text-gray-800 py-3 rounded-lg font-medium hover:bg-gray-100 transition-all disabled:opacity-50"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continue with Google
        </button>

        {/* Message */}
        {message && (
          <div
            className={`mt-4 p-3 rounded-lg text-sm ${
              message.toLowerCase().includes('error')
                ? 'bg-red-900/30 text-red-400 border border-red-800'
                : 'bg-green-900/30 text-green-400 border border-green-800'
            }`}
          >
            {message}
          </div>
        )}

        {/* Footer */}
        <p className="text-center text-xs text-[var(--phronai-text-muted)] mt-6">
          Voice-powered diagram creation with zero hallucinations.
        </p>
      </div>
    </div>
  );
}
