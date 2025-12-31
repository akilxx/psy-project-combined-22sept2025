import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTestReport, unlockReportWithSubscription } from '../api/testing';
import RippleButton from '../components/RippleButton';

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
                        await unlockReportWithSubscription(testResultId);
                        
                        // 3. If unlock succeeds, fetch the report again
                        const newData = await getTestReport(testResultId);
                        setReportData(newData);
                    } catch (unlockErr) {
                        console.error("Auto-unlock failed:", unlockErr);
                        
                        // Check if we got a response from the server
                        if (unlockErr.response) {
                            const status = unlockErr.response.status;
                            
                            // 4xx Errors (e.g. 403 Forbidden, 400 Bad Request)
                            // These are valid responses meaning "You are not allowed" -> Show Locked Screen
                            if (status >= 400 && status < 500) {
                                const backendMsg = unlockErr.response.data?.detail || "You do not have access to this report.";
                                setUnlockError(backendMsg);
                                setAccessDenied(true);
                            } else {
                                // 5xx Errors (e.g. 500 Internal Server Error)
                                // The server crashed -> Show Generic Error Screen
                                setError("Server error occurred while unlocking. Please try again later.");
                            }
                        } else {
                            // No response received (e.g. Offline / DNS failure)
                            // This is a Network Error -> Show Generic Error Screen
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
            <div className="h-screen w-screen bg-white flex flex-col items-center justify-center overflow-hidden">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-900 mb-4"></div>
                <h2 className="text-xl font-semibold text-gray-700">Loading Report...</h2>
                <p className="text-gray-500 text-sm mt-2">Verifying access rights</p>
            </div>
        );
    }

    if (accessDenied) {
        return (
            <div className="h-screen w-screen bg-white flex flex-col items-center justify-center relative overflow-hidden">
                <div className="max-w-md w-full px-4 sm:px-6">
                    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                        <div className="p-8 text-center">
                            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-blue-50 border border-blue-100 mb-6">
                                <svg className="h-8 w-8 text-blue-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-bold text-gray-900 mb-2">
                                Report Locked
                            </h2>
                            <p className="text-gray-500 mb-6">
                                Unlock this report to view your detailed psychometric analysis.
                            </p>

                            {unlockError && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-left flex items-start">
                                     <svg className="h-5 w-5 text-red-400 mt-0.5 mr-3 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                    <p className="text-sm text-red-700 font-medium">{unlockError}</p>
                                </div>
                            )}

                            <div className="space-y-3">
                                <RippleButton 
                                    onClick={() => navigate('/pricing')} 
                                    className="w-full bg-blue-900 hover:bg-blue-800 text-white font-semibold py-3 rounded-xl border border-transparent flex justify-center"
                                >
                                    View Subscription Plans
                                </RippleButton>
                                <button 
                                    onClick={() => navigate('/dashboard')}
                                    className="text-gray-500 hover:text-gray-800 text-sm font-medium transition-colors w-full"
                                >
                                    Return to Dashboard
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="h-screen w-screen bg-white flex flex-col items-center justify-center p-4">
                <div className="bg-white p-8 rounded-xl border border-red-100 max-w-md w-full text-center">
                    <div className="text-red-500 text-5xl mb-4">⚠️</div>
                    <h2 className="text-xl font-bold text-gray-800 mb-2">Something went wrong</h2>
                    <p className="text-gray-600 mb-6">{error}</p>
                    <RippleButton onClick={() => navigate('/dashboard')} className="w-full justify-center">
                        Return to Dashboard
                    </RippleButton>
                </div>
            </div>
        );
    }

    // ─── REPORT DISPLAY (Success) ────────────────────────────────────────
    
    // Get current block safely
    const currentBlock = reportData?.report_content?.[currentTraitIndex];

    if (!currentBlock) return null; // Safety check

    return (
        // Root: h-screen + overflow-hidden to remove scrollbar
        <div className="h-screen w-screen bg-white relative overflow-hidden flex flex-col">
            
            {/* Dark Styled Header - Compacted */}
            <div className="bg-gray-900 pb-12 shrink-0">
                <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-14">
                         <div className="flex items-center">
                            <button 
                                onClick={() => navigate('/dashboard')}
                                className="flex items-center text-gray-300 hover:text-white transition-colors"
                            >
                                <Chevron direction="left" className="w-5 h-5 mr-2" />
                                <span className="font-medium text-sm">Dashboard</span>
                            </button>
                        </div>
                        <div className="flex items-center space-x-4">
                            <button onClick={() => window.print()} className="text-gray-300 hover:text-white transition-colors p-2">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" /></svg>
                            </button>
                        </div>
                    </div>
                </nav>
                <header className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="md:flex md:items-center md:justify-between">
                        <div className="flex-1 min-w-0">
                            <h2 className="text-2xl font-bold leading-7 text-white sm:text-3xl sm:truncate">
                                Psychometric Insight Report
                            </h2>
                            <p className="mt-1 text-blue-200 text-sm">
                                Detailed analysis of your personality traits and percentiles.
                            </p>
                        </div>
                        <div className="mt-4 flex md:mt-0 md:ml-4">
                             <span className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-medium bg-blue-900 text-blue-100 border border-blue-700">
                                {reportData.access_method?.replace(/_/g, ' ') || 'Accessed'}
                            </span>
                        </div>
                    </div>
                </header>
            </div>

            {/* Main Content - Flex-1 to take remaining space, negative margin to overlap */}
            <main className="flex-1 -mt-10 w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-4 flex flex-col overflow-hidden">
                
                {/* Intro Card - Compacted */}
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-3 shrink-0">
                     <div className="p-3 sm:px-4">
                        <div className="flex items-center justify-between mb-1">
                            <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide">Summary</h3>
                            <p className="text-[10px] text-gray-500">
                                Completed: {new Date(reportData.created_at).toLocaleDateString()}
                            </p>
                        </div>
                        <p className="text-[11px] text-gray-600 leading-snug border-t border-gray-100 pt-2">
                            Your results have been processed successfully. Below is a breakdown of your performance across key traits relative to the population norm. 
                        </p>
                    </div>
                </div>

                {/* Navigable Single Card Layout - Flex-1 for centering/fitting */}
                <div className="w-full flex-1 flex flex-col justify-center min-h-0">
                    <div className="flex items-center justify-between gap-2 sm:gap-6 h-full max-h-[500px]">
                        
                        {/* Left Chevron */}
                        <button 
                            onClick={handlePrev}
                            className="p-2 rounded-full hover:bg-gray-50 text-gray-400 hover:text-blue-900 transition-all border border-transparent hover:border-gray-200 hidden sm:block shrink-0"
                            aria-label="Previous trait"
                        >
                            <Chevron direction="left" className="w-8 h-8" />
                        </button>

                        <button 
                            onClick={handlePrev}
                            className="p-1 rounded-full bg-white border border-gray-200 shadow-sm text-gray-500 sm:hidden shrink-0"
                            aria-label="Previous trait"
                        >
                            <Chevron direction="left" className="w-5 h-5" />
                        </button>

                        {/* The Single Active Card */}
                        <div className="flex-1 min-w-0 h-full flex flex-col" key={currentTraitIndex}>
                            <div className="flex flex-col bg-white rounded-2xl border border-gray-200 border-t-4 border-t-blue-900 h-full">
                                <div className="p-5 sm:p-8 flex-1 flex flex-col overflow-y-auto scrollbar-hide">
                                    <div className="flex justify-between items-start mb-4 shrink-0">
                                        <div>
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-900 uppercase tracking-wide border border-blue-100">
                                                Trait {currentTraitIndex + 1} / {reportData.report_content.length}
                                            </span>
                                            <h3 className="mt-2 text-xl font-bold text-gray-900">{currentBlock.trait}</h3>
                                        </div>
                                        <div className="text-right shrink-0">
                                            <p className="text-3xl font-extrabold text-blue-900">{currentBlock.percentile}<span className="text-lg text-gray-400 font-medium">%</span></p>
                                        </div>
                                    </div>

                                    {/* Progress Bar - Dark Blue */}
                                    <div className="w-full bg-gray-100 rounded-full h-2 mb-5 shrink-0">
                                        <div 
                                            className="bg-blue-900 h-2 rounded-full transition-all duration-1000" 
                                            style={{ width: `${currentBlock.percentile}%` }}
                                        ></div>
                                    </div>
                                    
                                    <div className="prose prose-sm prose-blue text-gray-600 leading-relaxed overflow-y-auto pr-2">
                                        {currentBlock.text.split('\n').map((paragraph, idx) => (
                                            <p key={idx} className={idx === 0 ? "" : "mt-3"}>
                                                {paragraph}
                                            </p>
                                        ))}
                                    </div>
                                </div>
                                <div className="bg-gray-50 p-3 border-t border-gray-200 rounded-b-2xl shrink-0">
                                    <p className="text-[10px] text-center text-gray-400 italic">
                                        Swipe or use arrows to view more traits
                                    </p>
                                </div>
                            </div>
                        </div>

                        <button 
                            onClick={handleNext}
                            className="p-1 rounded-full bg-white border border-gray-200 shadow-sm text-gray-500 sm:hidden shrink-0"
                            aria-label="Next trait"
                        >
                            <Chevron direction="right" className="w-5 h-5" />
                        </button>

                        <button 
                            onClick={handleNext}
                            className="p-2 rounded-full hover:bg-gray-50 text-gray-400 hover:text-blue-900 transition-all border border-transparent hover:border-gray-200 hidden sm:block shrink-0"
                            aria-label="Next trait"
                        >
                            <Chevron direction="right" className="w-8 h-8" />
                        </button>
                    </div>

                    {/* Pagination Dots - Dark Blue */}
                    <div className="flex justify-center mt-4 gap-2 shrink-0">
                        {reportData.report_content.map((_, idx) => (
                            <button
                                key={idx}
                                onClick={() => setCurrentTraitIndex(idx)}
                                aria-label={`Go to trait ${idx + 1}`}
                                className={`h-1.5 rounded-full transition-all duration-300 ${
                                    idx === currentTraitIndex ? 'w-6 bg-blue-900' : 'w-1.5 bg-gray-300 hover:bg-gray-400'
                                }`}
                            />
                        ))}
                    </div>
                </div>

                <div className="mt-4 text-center shrink-0">
                    <button 
                        onClick={() => navigate('/dashboard')}
                        className="text-gray-400 hover:text-gray-900 text-xs font-medium transition-colors"
                    >
                        Return to Dashboard
                    </button>
                </div>

            </main>

            {/* Inline Styles for hiding scrollbar but allowing scroll */}
            <style>{`
                .scrollbar-hide::-webkit-scrollbar {
                    display: none;
                }
                .scrollbar-hide {
                    -ms-overflow-style: none;
                    scrollbar-width: none;
                }
            `}</style>
        </div>
    );
};

export default Report;