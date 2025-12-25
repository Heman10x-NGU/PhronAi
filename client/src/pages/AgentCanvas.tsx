import { useEffect, useRef, useState, useCallback } from 'react';
import { Tldraw, type Editor, getSnapshot } from 'tldraw';
import 'tldraw/tldraw.css';
import { useAuth } from '../contexts/AuthContext';
import { 
  createGraphState, 
  applyAction, 
  layoutGraph, 
  serializeGraphState, 
  extractGraphFromSnapshot, 
  type GraphState 
} from '../lib/graphLayout';
import { renderLayout } from '../lib/tldrawShapes';
import { DiagramNodeUtil } from '../lib/DiagramNodeShape';
import type { SketchResponse } from '../types/sketch';

const customShapeUtils = [DiagramNodeUtil];

type AgentStatus = 'idle' | 'listening' | 'transcribing' | 'reasoning' | 'rendering' | 'error';

const STATUS_LABELS: Record<AgentStatus, string> = {
  idle: 'Voice Agent',
  listening: 'Listening...',
  transcribing: 'Processing Audio...',
  reasoning: 'AI Thinking...',
  rendering: 'Drawing...',
  error: 'Error',
};

export function AgentCanvas() {
  const { signOut, session } = useAuth();
  const [editor, setEditor] = useState<Editor | null>(null);
  const [transcript, setTranscript] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [showTranscriptModal, setShowTranscriptModal] = useState(false);
  
  const graphStateRef = useRef<GraphState>(createGraphState());
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const autoSaveTimerRef = useRef<number | null>(null);

  // WebSocket connection
  useEffect(() => {
    if (!session?.access_token) return;

    // Use VITE_API_WS_URL from environment, fallback to localhost for dev
    const wsUrl = import.meta.env.VITE_API_WS_URL || 'ws://localhost:8000/ws/agent/';
    const wsUrlWithToken = `${wsUrl}?token=${session.access_token}`;
    const ws = new WebSocket(wsUrlWithToken);

    ws.onopen = () => {
      console.log('Connected to PHRONAI');
      setIsConnected(true);
      setStatus('idle');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case 'connected':
            console.log('Server welcome:', data.message);
            break;
          case 'transcript':
            setTranscript(data.text);
            setStatus('reasoning');
            break;
          case 'actions':
            handleActions(data.actions);
            break;
          case 'error':
            console.error('Server error:', data.message);
            setStatus('error');
            setTimeout(() => setStatus('idle'), 3000);
            break;
        }
      } catch {
        if (typeof event.data === 'string' && !event.data.startsWith('{')) {
          setTranscript(event.data);
          setStatus('reasoning');
        }
      }
    };

    ws.onerror = (err) => {
      console.warn('⚠️ WebSocket error - Backend running?', err);
      setIsConnected(false);
      setStatus('error');
    };

    ws.onclose = () => setIsConnected(false);

    wsRef.current = ws;
    return () => ws.close();
  }, [session]);

  const handleActions = useCallback((actions: SketchResponse['actions']) => {
    if (!editor || actions.length === 0) {
      setStatus('idle');
      return;
    }
    
    setStatus('rendering');
    const graphState = graphStateRef.current;
    
    // Debug: Log incoming actions
    console.log('📥 Received actions:', JSON.stringify(actions, null, 2));
    console.log('📊 Current nodes before:', Array.from(graphState.nodes.keys()));
    
    for (const action of actions) {
      const success = applyAction(graphState, action);
      console.log(`  ${success ? '✅' : '❌'} ${action.action}: ${action.id}`);
    }
    
    console.log('📊 Nodes after:', Array.from(graphState.nodes.keys()));
    
    layoutGraph(graphState)
      .then((layout) => {
        console.log('🎨 Rendering layout:', layout.nodes.length, 'nodes,', layout.edges.length, 'edges');
        renderLayout(editor, layout.nodes, layout.edges);
        setStatus('idle');
        setSaveStatus('unsaved');
        if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
        autoSaveTimerRef.current = window.setTimeout(() => syncCanvas(), 3000);
      })
      .catch((err) => {
        console.error('Layout error:', err);
        setStatus('error');
      });
  }, [editor]);

  const syncCanvas = useCallback(() => {
    if (!editor || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setSaveStatus('saving');
    const { document } = getSnapshot(editor.store);
    const graphState = extractGraphFromSnapshot(document);
    graphStateRef.current = graphState;
    wsRef.current.send(JSON.stringify({
      type: 'canvas_sync',
      snapshot: JSON.stringify(document),
      graph: serializeGraphState(graphState),
    }));
    setSaveStatus('saved');
  }, [editor]);

  const startRecording = useCallback(async () => {
    if (!wsRef.current || !isConnected) return;
    try {
      setIsRecording(true);
      setStatus('listening');
      setTranscript('');
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true }
      });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
          ? 'audio/webm;codecs=opus' : undefined
      });
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (wsRef.current?.readyState === WebSocket.OPEN && audioBlob.size > 0) {
          setStatus('transcribing');
          const graphSync = serializeGraphState(graphStateRef.current);
          wsRef.current.send(JSON.stringify({ ...graphSync, type: 'graph_sync' }));
          wsRef.current.send(audioBlob);
        } else {
          setStatus('idle');
        }
        stream.getTracks().forEach(track => track.stop());
      };
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100);
    } catch (error) {
      console.error('Recording error:', error);
      setIsRecording(false);
      setStatus('error');
    }
  }, [isConnected]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current?.stop();
    }
    setIsRecording(false);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0f0f1a] overflow-hidden">
      {/* HEADER CONTROLS - Fixed Top Bar */}
      <header className="h-16 px-6 flex items-center justify-between bg-[#1a1a2e]/90 backdrop-blur-md border-b border-violet-500/20 z-50 shadow-lg">
        
        {/* Left: Brand */}
        <div className="flex items-center gap-4 min-w-[200px]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-violet-500/20">
              P
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent tracking-tight">
              PHRONAI
            </span>
          </div>
          <div className={`w-2 h-2 rounded-full ring-2 ring-black/20 ${isConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-red-500'}`} />
          <a
            href="https://www.linkedin.com/in/heman10x/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-500 hover:text-violet-400 transition-colors flex items-center gap-1"
          >
            <span>by</span>
            <span className="font-medium">Hemant</span>
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
            </svg>
          </a>
        </div>

        {/* Center: Dynamic Voice Controls */}
        <div className="flex-1 flex items-center justify-center gap-4 max-w-2xl px-4">
          
          {/* Record Button Pill */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={!isConnected}
            className={`
              flex items-center gap-3 px-5 py-2.5 rounded-full transition-all duration-300
              font-medium text-sm tracking-wide shadow-lg border
              ${isRecording 
                ? 'bg-red-500/10 border-red-500/50 text-red-500 recording-pulse hover:bg-red-500/20' 
                : isConnected
                  ? 'bg-violet-600 text-white border-transparent hover:bg-violet-500 hover:shadow-violet-500/25 hover:-translate-y-0.5' 
                  : 'bg-gray-800 text-gray-500 border-gray-700 cursor-not-allowed'
              }
            `}
          >
            {isRecording ? (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                </span>
                <span>Stop Recording</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" />
                </svg>
                <span>{STATUS_LABELS[status]}</span>
              </>
            )}
          </button>

          {/* Transcript / Status Display - Clickable to expand */}
          {(transcript || status !== 'idle') && (
            <div 
              className="flex px-4 py-2 bg-white/5 border border-white/10 rounded-full animate-fade-in backdrop-blur-sm max-w-[400px] gap-3 items-center cursor-pointer hover:bg-white/10 transition-colors group"
              title="Click to view full transcript"
              onClick={() => transcript && setShowTranscriptModal(true)}
            >
               {status !== 'idle' && status !== 'listening' && (
                  <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
               )}
               <p className="text-sm text-gray-200 truncate font-medium group-hover:text-white">
                 {transcript || 'Processing...'}
               </p>
               {transcript && transcript.length > 40 && (
                 <span className="text-xs text-violet-400 flex-shrink-0">⋯</span>
               )}
            </div>
          )}

        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-4 min-w-[200px] justify-end">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg border border-white/5">
             <div className={`w-1.5 h-1.5 rounded-full ${
                saveStatus === 'saved' ? 'bg-emerald-400' :
                saveStatus === 'saving' ? 'bg-yellow-400 animate-pulse' : 'bg-orange-400'
             }`} />
             <span className="text-xs text-gray-400 font-medium">
               {saveStatus === 'saved' ? 'Saved' : saveStatus === 'saving' ? 'Saving...' : 'Unsaved'}
             </span>
          </div>

          <button
            onClick={signOut}
            className="text-sm font-medium text-gray-400 hover:text-white transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* CANVAS - Full height minus header */}
      <div className="flex-1 relative z-0">
        <Tldraw onMount={setEditor} shapeUtils={customShapeUtils} />
      </div>

      {/* Transcript Modal */}
      {showTranscriptModal && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
          onClick={() => setShowTranscriptModal(false)}
        >
          <div 
            className="bg-[#1a1a2e] border border-violet-500/30 rounded-2xl p-6 max-w-lg w-full shadow-2xl animate-fade-in"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Your Voice Command</h3>
              <button 
                onClick={() => setShowTranscriptModal(false)}
                className="text-gray-400 hover:text-white transition-colors text-xl"
              >
                ✕
              </button>
            </div>
            <div className="bg-black/30 rounded-xl p-4 border border-white/5">
              <p className="text-gray-200 leading-relaxed">"{transcript}"</p>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setShowTranscriptModal(false)}
                className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-500 transition-colors text-sm font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
