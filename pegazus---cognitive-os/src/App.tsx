import React, { useState } from 'react';
import { AppRoute, Locale, UserProfile, LearningPath, SessionStats } from './types';
import { I18nProvider } from './i18n/context';
import { AppShell } from './components/common/AppShell';
import { OfflineBanner } from './components/common/OfflineBanner';

// Screen components
import { AuthSignInScreen } from './screens/AuthSignInScreen';
import { AuthCallbackScreen } from './screens/AuthCallbackScreen';
import { OnboardAgeScreen } from './screens/OnboardAgeScreen';
import { ConsentWaitScreen } from './screens/ConsentWaitScreen';
import { HomeScreen } from './screens/HomeScreen';
import { PathCreateScreen } from './screens/PathCreateScreen';
import { PathViewScreen } from './screens/PathViewScreen';
import { DiagnosticScreen } from './screens/DiagnosticScreen';
import { SessionScreen } from './screens/SessionScreen';
import { SessionSummaryScreen } from './screens/SessionSummaryScreen';
import { SessionRestScreen } from './screens/SessionRestScreen';
import { SocraticScreen } from './screens/SocraticScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { SettingsByoScreen } from './screens/SettingsByoScreen';
import { SettingsDeleteScreen } from './screens/SettingsDeleteScreen';

// Default initial learning path (Single Variable Calculus: Limits & Derivatives)
const defaultPath: LearningPath = {
  id: 'path-calc-1',
  title: 'Single Variable Calculus',
  subject: 'Limits, Continuous Functions, and Differential Derivations',
  targetDate: '2026-11-15',
  dailyBudgetMinutes: 30,
  status: 'ACTIVE',
  criticalPathMinutes: 1440, // 24 hours total
  fitWarning: {
    isOverloaded: false,
    requiredDailyMinutes: 28
  },
  nodes: [
    {
      id: 'node-1',
      title: 'Limits & Indeterminate Forms',
      mathTitle: '\\lim_{x \\to a} \\frac{f(x)}{g(x)}',
      description: 'Algebraic cancellation of removable singularities and factorization of quadratic limits.',
      status: 'mastered',
      masteryPercent: 100,
      dueDate: 'Tomorrow',
      estimatedMinutes: 20,
      prerequisites: [],
      sourceAttribution: 'OpenStax Calculus Vol 1, Section 2.3 · CC-BY 4.0',
      scaffoldTier: 3
    },
    {
      id: 'node-2',
      title: 'Power Rule & Polynomial Derivatives',
      mathTitle: '\\frac{d}{dx}\\left[x^n\\right] = n x^{n-1}',
      description: 'Application of the basic power rule, linearity, and sum/difference derivative formulas.',
      status: 'due_review',
      masteryPercent: 88,
      dueDate: 'Today',
      estimatedMinutes: 15,
      prerequisites: ['node-1'],
      sourceAttribution: 'MIT OpenCourseWare 18.01, Lecture 3 · CC-BY-NC-SA 4.0',
      scaffoldTier: 2
    },
    {
      id: 'node-3',
      title: 'Chain Rule with Composite Functions',
      mathTitle: '\\frac{d}{dx}[f(g(x))] = f\'(g(x)) \\cdot g\'(x)',
      description: 'Decomposition of composite functions into inner and outer terms for symbolic derivation.',
      status: 'frontier',
      masteryPercent: 45,
      dueDate: 'Today',
      estimatedMinutes: 25,
      prerequisites: ['node-2'],
      sourceAttribution: 'OpenStax Calculus Vol 1, Section 3.6 · CC-BY 4.0',
      scaffoldTier: 1
    },
    {
      id: 'node-4',
      title: 'Product & Quotient Derivations',
      mathTitle: '\\frac{d}{dx}[u \\cdot v] = u\'v + uv\'',
      description: 'Systematic symbolic derivation of rational and multiplicative expressions.',
      status: 'locked',
      masteryPercent: 0,
      dueDate: 'Scheduled',
      estimatedMinutes: 30,
      prerequisites: ['node-3'],
      sourceAttribution: 'Stewart Calculus Early Transcendentals, Section 3.2',
      scaffoldTier: 1
    },
    {
      id: 'node-5',
      title: 'Fundamental Theorem of Calculus',
      mathTitle: '\\int_{a}^{b} f(x)\\,dx = F(b) - F(a)',
      description: 'Connecting differentiation with definite Riemann summation.',
      status: 'locked',
      masteryPercent: 0,
      dueDate: 'Scheduled',
      estimatedMinutes: 40,
      prerequisites: ['node-4'],
      sourceAttribution: 'MIT OpenCourseWare 18.01, Lecture 19 · CC-BY-NC-SA 4.0',
      scaffoldTier: 1
    }
  ]
};

export default function App() {
  const [locale, setLocale] = useState<Locale>('en');
  const [currentRoute, setCurrentRoute] = useState<AppRoute>('HOME');

  // User state
  const [user, setUser] = useState<UserProfile | null>({
    email: 'owen.alexlol321@gmail.com',
    locale: 'en',
    birthYear: 1998,
    isMinor: false,
    guardianConsentGiven: true,
    preferredSessionMinutes: 25,
    targetRetention: 0.90,
    microBreakIntervalMinutes: 5,
    focusPrimingEnabled: false,
    isOffline: false
  });

  // Active learning path
  const [activePath, setActivePath] = useState<LearningPath | null>(defaultPath);

  // Session stats for summary
  const [lastSessionStats, setLastSessionStats] = useState<SessionStats>({
    durationSeconds: 940,
    itemsCompleted: 2,
    reviewsDone: 1,
    frontierAdvanced: 1,
    nodesUpdated: ['Power Rule & Polynomial Derivatives', 'Chain Rule with Composite Functions']
  });

  // Offline simulator flag
  const [isOffline, setIsOffline] = useState(false);

  // Auth gate checks
  if (!user) {
    return (
      <I18nProvider locale={locale} setLocale={setLocale}>
        <AuthSignInScreen
          locale={locale}
          onLocaleChange={setLocale}
          onSignInSuccess={(email) => {
            setUser({
              email,
              locale,
              birthYear: null,
              isMinor: false,
              guardianConsentGiven: false,
              preferredSessionMinutes: 25,
              targetRetention: 0.90,
              microBreakIntervalMinutes: 5,
              focusPrimingEnabled: false,
              isOffline: false
            });
            setCurrentRoute('AUTH_CALLBACK');
          }}
        />
      </I18nProvider>
    );
  }

  if (currentRoute === 'AUTH_CALLBACK') {
    return (
      <I18nProvider locale={locale} setLocale={setLocale}>
        <AuthCallbackScreen
          onComplete={() => {
            if (user.birthYear === null) {
              setCurrentRoute('ONBOARD_AGE');
            } else {
              setCurrentRoute('HOME');
            }
          }}
        />
      </I18nProvider>
    );
  }

  if (user.birthYear === null || currentRoute === 'ONBOARD_AGE') {
    return (
      <I18nProvider locale={locale} setLocale={setLocale}>
        <OnboardAgeScreen
          onYearSelected={(year, isMinor) => {
            setUser({
              ...user,
              birthYear: year,
              isMinor
            });
            if (isMinor && !user.guardianConsentGiven) {
              setCurrentRoute('CONSENT_WAIT');
            } else {
              setCurrentRoute('HOME');
            }
          }}
        />
      </I18nProvider>
    );
  }

  if (user.isMinor && !user.guardianConsentGiven && currentRoute === 'CONSENT_WAIT') {
    return (
      <I18nProvider locale={locale} setLocale={setLocale}>
        <ConsentWaitScreen
          onBypassConsent={() => {
            setUser({ ...user, guardianConsentGiven: true });
            setCurrentRoute('HOME');
          }}
          onSignOut={() => {
            setUser(null);
            setCurrentRoute('AUTH_SIGNIN');
          }}
        />
      </I18nProvider>
    );
  }

  // Handle path creation
  const handleCreatePath = (pathData: {
    subject: string;
    targetDate?: string;
    dailyBudgetMinutes: number;
    syllabusFileName?: string;
  }) => {
    const newPath: LearningPath = {
      id: `path-${Date.now()}`,
      title: pathData.subject.split(':')[0] || pathData.subject,
      subject: pathData.subject,
      targetDate: pathData.targetDate,
      dailyBudgetMinutes: pathData.dailyBudgetMinutes,
      status: 'REFINING',
      criticalPathMinutes: 1200,
      nodes: [
        {
          id: 'np-1',
          title: 'Foundations & Algebraic Primitives',
          mathTitle: 'a x + b = 0',
          description: 'Fundamental algebraic axioms and balance equations.',
          status: 'mastered',
          masteryPercent: 100,
          dueDate: 'Tomorrow',
          estimatedMinutes: 20,
          prerequisites: [],
          sourceAttribution: 'OpenStax Algebra · CC-BY 4.0',
          scaffoldTier: 3
        },
        {
          id: 'np-2',
          title: 'Direct Limit Evaluation',
          mathTitle: '\\lim_{x \\to c} f(x) = L',
          description: 'Substitution laws and continuity boundaries.',
          status: 'frontier',
          masteryPercent: 30,
          dueDate: 'Today',
          estimatedMinutes: 25,
          prerequisites: ['np-1'],
          sourceAttribution: 'MIT OCW · CC-BY-NC-SA 4.0',
          scaffoldTier: 1
        },
        {
          id: 'np-3',
          title: 'Derivative by First Principles',
          mathTitle: 'f\'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}',
          description: 'Infinitesimal secant-to-tangent slope convergence.',
          status: 'drafting',
          masteryPercent: 0,
          dueDate: 'Scheduled',
          estimatedMinutes: 35,
          prerequisites: ['np-2'],
          sourceAttribution: 'Calculus Early Transcendentals',
          scaffoldTier: 1
        }
      ]
    };
    setActivePath(newPath);
    setCurrentRoute('PATH_VIEW');

    // Simulate SSE refinement completing
    setTimeout(() => {
      setActivePath((prev) => (prev ? { ...prev, status: 'ACTIVE' } : prev));
    }, 2500);
  };

  const handleFinishSession = (stats: SessionStats) => {
    setLastSessionStats(stats);
    // Mark reviewed node as updated
    if (activePath) {
      const updatedNodes = activePath.nodes.map((n) => {
        if (n.status === 'due_review') {
          return { ...n, status: 'mastered' as const, masteryPercent: Math.min(100, n.masteryPercent + 10) };
        }
        if (n.status === 'frontier') {
          return { ...n, masteryPercent: Math.min(100, n.masteryPercent + 35) };
        }
        return n;
      });
      setActivePath({ ...activePath, nodes: updatedNodes });
    }
    setCurrentRoute('SESSION_SUMMARY');
  };

  return (
    <I18nProvider locale={locale} setLocale={setLocale}>
      <OfflineBanner isOffline={isOffline} />
      <AppShell
        currentRoute={currentRoute}
        onNavigate={(route) => setCurrentRoute(route)}
        locale={locale}
        onLocaleChange={setLocale}
        isOffline={isOffline}
        onToggleOffline={() => setIsOffline(!isOffline)}
      >
        {currentRoute === 'HOME' && (
          <HomeScreen
            activePath={activePath}
            dueReviewsCount={activePath?.nodes.filter((n) => n.status === 'due_review').length || 0}
            budgetMinutesRemaining={25}
            onStartSession={() => setCurrentRoute('SESSION')}
            onCreatePath={() => setCurrentRoute('PATH_CREATE')}
            onAskQuick={() => setCurrentRoute('SOCRATIC')}
            onViewPath={() => setCurrentRoute('PATH_VIEW')}
          />
        )}

        {currentRoute === 'PATH_VIEW' && (
          <PathViewScreen
            path={activePath}
            onStartPractice={() => setCurrentRoute('SESSION')}
            onStartDiagnostic={() => setCurrentRoute('DIAGNOSTIC')}
            onCreateNewPath={() => setCurrentRoute('PATH_CREATE')}
          />
        )}

        {currentRoute === 'PATH_CREATE' && (
          <PathCreateScreen
            isMinor={user.isMinor}
            onCreatePath={handleCreatePath}
            onCancel={() => setCurrentRoute('HOME')}
          />
        )}

        {currentRoute === 'DIAGNOSTIC' && (
          <DiagnosticScreen
            onComplete={() => setCurrentRoute('SESSION')}
            onExit={() => setCurrentRoute('PATH_VIEW')}
          />
        )}

        {currentRoute === 'SESSION' && (
          <SessionScreen
            path={activePath}
            isOffline={isOffline}
            focusPrimingEnabled={user.focusPrimingEnabled}
            onFinishSession={handleFinishSession}
            onExitSession={() => setCurrentRoute('HOME')}
          />
        )}

        {currentRoute === 'SESSION_SUMMARY' && (
          <SessionSummaryScreen
            stats={lastSessionStats}
            onContinueToRest={() => setCurrentRoute('SESSION_REST')}
            onSkipRest={() => setCurrentRoute('HOME')}
          />
        )}

        {currentRoute === 'SESSION_REST' && (
          <SessionRestScreen onReturnHome={() => setCurrentRoute('HOME')} />
        )}

        {currentRoute === 'SOCRATIC' && (
          <SocraticScreen onReturnHome={() => setCurrentRoute('HOME')} />
        )}

        {currentRoute === 'SETTINGS' && (
          <SettingsScreen
            user={user}
            onUpdateProfile={(updates) => setUser({ ...user, ...updates })}
            onNavigateByo={() => setCurrentRoute('SETTINGS_BYO')}
            onNavigateDelete={() => setCurrentRoute('SETTINGS_DELETE')}
            onSignOut={() => {
              setUser(null);
              setCurrentRoute('AUTH_SIGNIN');
            }}
          />
        )}

        {currentRoute === 'SETTINGS_BYO' && (
          <SettingsByoScreen
            currentKey={user.openRouterApiKey}
            isMinor={user.isMinor}
            onSaveKey={(key) => {
              setUser({ ...user, openRouterApiKey: key });
              setCurrentRoute('SETTINGS');
            }}
            onRemoveKey={() => {
              setUser({ ...user, openRouterApiKey: undefined });
              setCurrentRoute('SETTINGS');
            }}
            onBack={() => setCurrentRoute('SETTINGS')}
          />
        )}

        {currentRoute === 'SETTINGS_DELETE' && (
          <SettingsDeleteScreen
            onBack={() => setCurrentRoute('SETTINGS')}
            onConfirmDelete={() => {
              setUser(null);
              setActivePath(null);
              setCurrentRoute('AUTH_SIGNIN');
            }}
          />
        )}
      </AppShell>
    </I18nProvider>
  );
}
