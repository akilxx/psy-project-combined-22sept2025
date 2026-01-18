import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTestReport, unlockReportWithSubscription } from '../api/testing';
import clsx from 'clsx';

// -----------------------------------------------------------------------------
// RETRY HELPER (Fixes Race Condition)
// -----------------------------------------------------------------------------

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const retryUnlock = async (fn, retries = 3, delay = 1500) => {
    try {
        return await fn();
    } catch (err) {
        // If it's a client error (e.g. 403, 400) or we ran out of retries, stop.
        if ((err.response && err.response.status < 500) || retries <= 0) {
            throw err;
        }
        // Wait and try again
        await wait(delay);
        return retryUnlock(fn, retries - 1, delay);
    }
};

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------------------------

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// -----------------------------------------------------------------------------
// LOCAL COMPONENTS (For consistent styling independent of global components)
// -----------------------------------------------------------------------------

const Chevron = ({ direction, className }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        {direction === 'left' ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        )}
    </svg>
);

// -----------------------------------------------------------------------------
// MAIN REPORT COMPONENT
// -----------------------------------------------------------------------------

const Report = () => {
    const { testResultId } = useParams();
    const navigate = useNavigate();
    
    // State
    const [reportData, setReportData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [accessDenied, setAccessDenied] = useState(false);
    const [unlockError, setUnlockError] = useState(null);
    const [error, setError] = useState(null);
    const [currentTraitIndex, setCurrentTraitIndex] = useState(0);

    // ─── DATA LOADING LOGIC ─────────────────────────────────────────────
    useEffect(() => {
        const loadReportStrategy = async () => {
            setLoading(true);
            setAccessDenied(false);
            setUnlockError(null);
            
            try {
                // 1. Try to fetch the report (checks if already paid/unlocked)
                const data = await getTestReport(testResultId);
                setReportData(data);
            } catch (err) {
                // 2. If 404, it means we need to try auto-unlocking via subscription
                if (err.response && err.response.status === 404) {
                    try {
                        console.log("Report not found. Attempting auto-unlock via subscription...");
                        
                        // --- CHANGED: Wrapped in retryUnlock ---
                        await retryUnlock(() => unlockReportWithSubscription(testResultId), 3, 1500);
                        // ---------------------------------------
                        
                        // 3. If unlock succeeds, fetch the report again
                        const newData = await getTestReport(testResultId);
                        setReportData(newData);
                    } catch (unlockErr) {
                        console.error("Auto-unlock failed:", unlockErr);
                        
                        if (unlockErr.response) {
                            const status = unlockErr.response.status;
                            
                            if (status >= 400 && status < 500) {
                                const backendMsg = unlockErr.response.data?.detail || "You do not have access to this report.";
                                setUnlockError(backendMsg);
                                setAccessDenied(true);
                            } else {
                                setError("Server error occurred while unlocking. Please try again later.");
                            }
                        } else {
                            setError("Network error. Please check your internet connection.");
                        }
                    }
                } else {
                    console.error("Unexpected error:", err);
                    setError("An unexpected error occurred while loading the report.");
                }
            } finally {
                setLoading(false);
            }
        };

        if (testResultId) {
            loadReportStrategy();
        }
    }, [testResultId]);

    // ─── NAVIGATION HANDLERS ─────────────────────────────────────────────
    const handleNext = () => {
        if (!reportData?.report_content) return;
        setCurrentTraitIndex((prev) => (prev + 1) % reportData.report_content.length);
    };

    const handlePrev = () => {
        if (!reportData?.report_content) return;
        setCurrentTraitIndex((prev) => 
            prev === 0 ? reportData.report_content.length - 1 : prev - 1
        );
    };

    // ─── RENDER STATES ───────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="mx-auto max-w-5xl px-4 py-10">
                <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-slate-500">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4 mx-auto"></div>
                    <h2 className="text-xl font-semibold text-slate-700">Loading your report</h2>
                    <p className="text-slate-500 text-sm mt-2">Verifying access rights…</p>
                </div>
            </div>
        );
    }

    if (accessDenied) {
        return (
            <div className="mx-auto max-w-5xl px-4 py-10">
                <div className="rounded-2xl border border-dashed border-slate-300 p-8 bg-slate-50">
                    <div className="max-w-md mx-auto text-center">
                        <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-indigo-50 border border-indigo-100 mb-6">
                            <svg className="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                        <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                            Report access required
                        </h2>
                        <p className="text-slate-600 mb-6">
                            Unlock this report to view your detailed psychometric analysis and insights.
                        </p>

                        {unlockError && (
                            <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                                {unlockError}
                            </div>
                        )}

                        <div className="space-y-3">
                            <button
                                onClick={() => navigate('/subscription')}
                                className="w-full rounded-xl bg-indigo-600 py-3 text-white font-semibold shadow hover:bg-indigo-500 transition"
                            >
                                View subscription plans
                            </button>
                            <button
                                onClick={() => navigate('/dashboard')}
                                className="w-full text-slate-600 hover:text-slate-900 text-sm font-medium transition-colors"
                            >
                                Return to Dashboard
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="mx-auto max-w-5xl px-4 py-10">
                <div className="rounded-2xl border border-red-200 bg-red-50 p-8">
                    <div className="max-w-md mx-auto text-center">
                        <h2 className="text-xl font-semibold text-slate-900 mb-2">Something went wrong</h2>
                        <p className="text-slate-600 mb-6">{error}</p>
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="w-full rounded-xl bg-indigo-600 py-3 text-white font-semibold shadow hover:bg-indigo-500 transition"
                        >
                            Return to Dashboard
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // ─── REPORT DISPLAY (Success) ────────────────────────────────────────

    // Get current block safely
    const currentBlock = reportData?.report_content?.[currentTraitIndex];

    if (!currentBlock) return null; // Safety check

    return (
        <div className="mx-auto max-w-5xl px-4 py-10">
            {/* Page Header */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="inline-flex items-center text-sm font-medium text-slate-600 hover:text-slate-900 transition"
                    >
                        <Chevron direction="left" className="w-4 h-4 mr-1" />
                        Back to Dashboard
                    </button>
                    <button
                        onClick={() => window.print()}
                        className="inline-flex items-center text-sm font-medium text-slate-600 hover:text-slate-900 transition"
                    >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                        </svg>
                        Print
                    </button>
                </div>
                <div className="flex items-center justify-between">
                    <h1 className="text-3xl font-semibold text-slate-900">Test Report</h1>
                    <div className="flex items-center gap-3">
                        <p className="text-sm text-slate-600">
                            Completed on {formatDate(reportData.created_at)}
                        </p>
                        {reportData.access_method && (
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-500">Accessed via</span>
                                <span className="inline-flex items-center rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
                                    {reportData.access_method.replace(/_/g, ' ')}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Trait Analysis Card */}
            <div className="rounded-2xl bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-slate-900">Trait Analysis</h2>
                    <div className="flex gap-2">
                        <button
                            onClick={handlePrev}
                            className="inline-flex items-center justify-center rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-200 hover:text-indigo-700"
                            aria-label="Previous trait"
                        >
                            <Chevron direction="left" className="w-4 h-4 mr-1" />
                            Previous
                        </button>
                        <button
                            onClick={handleNext}
                            className="inline-flex items-center justify-center rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-200 hover:text-indigo-700"
                            aria-label="Next trait"
                        >
                            Next
                            <Chevron direction="right" className="w-4 h-4 ml-1" />
                        </button>
                    </div>
                </div>

                {/* Current Trait Card */}
                <div className="rounded-2xl border border-indigo-500 shadow-lg ring-2 ring-indigo-200 p-6">
                    <div className="flex items-start justify-between gap-3 mb-4">
                        <div className="flex-1">
                            <span className="inline-flex items-center rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
                                Trait {currentTraitIndex + 1} of {reportData.report_content.length}
                            </span>
                            <h3 className="mt-3 text-xl font-semibold text-slate-900">
                                {currentBlock.trait}
                            </h3>
                        </div>
                        <div className="text-right">
                            <p className="text-3xl font-semibold text-slate-900">
                                {currentBlock.percentile}
                                <span className="text-sm font-normal text-slate-500 ml-1">
                                    percentile
                                </span>
                            </p>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-100 rounded-full h-2 mb-4">
                        <div
                            className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${currentBlock.percentile}%` }}
                        ></div>
                    </div>

                    {/* Trait Description */}
                    <div className="mt-4 text-sm text-slate-600 leading-relaxed">
                        {currentBlock.text.split('\n').map((paragraph, pIdx) => (
                            <p key={pIdx} className={pIdx === 0 ? "" : "mt-3"}>
                                {paragraph}
                            </p>
                        ))}
                    </div>
                </div>

                {/* Pagination Dots */}
                <div className="flex justify-center mt-6 gap-2">
                    {reportData.report_content.map((_, idx) => (
                        <button
                            key={idx}
                            onClick={() => setCurrentTraitIndex(idx)}
                            aria-label={`Go to trait ${idx + 1}`}
                            className={clsx(
                                'h-2 rounded-full transition-all duration-300',
                                idx === currentTraitIndex
                                    ? 'w-8 bg-indigo-600'
                                    : 'w-2 bg-slate-300 hover:bg-slate-400'
                            )}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Report;