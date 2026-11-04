import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  RotateCcw,
  Bot,
  User,
  Wrench,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';
import { ChatMessage } from '../types/api';
import { sendChatMessage } from '../services/api';

interface ExtendedChatMessage extends ChatMessage {
  source_model?: string;
  is_ai_generated?: boolean;
}

interface MissionChatbotProps {
  imageId: string;
  isReasoningConfigured: boolean;
  reasoningModelName?: string;
}

const SUGGESTED_QUESTIONS = [
  "Why did RoverMind select this route instead of going straight?",
  "How many obstacle cells were detected in this frame?",
  "What happens if rocky terrain has a traversal cost of 10?",
  "Why are sunsets blue on Mars?",
  "How tall is Olympus Mons compared to Mount Everest?",
  "How does RoverMind use SAM 3.1 to segment terrain?",
  "Is this route guaranteed physically safe for a rover?",
];

export const MissionChatbot: React.FC<MissionChatbotProps> = ({
  imageId,
  isReasoningConfigured,
  reasoningModelName = 'llama-3.3-70b-instruct',
}) => {
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [showHelpPanel, setShowHelpPanel] = useState(false);
  const [expandedToolIdx, setExpandedToolIdx] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Reset conversation when imageId changes to ensure strict mission scoping
  useEffect(() => {
    setMessages([]);
    setConversationId(undefined);
  }, [imageId]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || isLoading) return;

    const userMsg: ExtendedChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);

    try {
      if (text.toLowerCase().includes('what happens') || text.toLowerCase().includes('cost')) {
        setActiveTool('Executing compare_routes...');
      } else if (text.toLowerCase().includes('how many') || text.toLowerCase().includes('count')) {
        setActiveTool('Executing get_terrain_distribution...');
      } else {
        setActiveTool('Consulting mission intelligence...');
      }

      const res = await sendChatMessage(imageId, text, conversationId);
      setConversationId(res.conversation_id);

      const assistantMsg: ExtendedChatMessage = {
        role: 'assistant',
        content: res.reply,
        timestamp: new Date().toLocaleTimeString(),
        tool_calls: res.tool_calls_executed,
        source_model: res.source_model,
        is_ai_generated: res.is_ai_generated,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ExtendedChatMessage = {
        role: 'assistant',
        content: `Error communicating with mission intelligence: ${err.message || 'Unknown network error'}.`,
        timestamp: new Date().toLocaleTimeString(),
        source_model: 'error',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setActiveTool(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleResetConversation = () => {
    setMessages([]);
    setConversationId(undefined);
  };

  return (
    <div className="hud-panel corner-bracket border-mars-750 flex flex-col transition-all">
      {/* Header */}
      <div className="p-4 border-b border-mars-800 flex items-center justify-between bg-mars-900/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-mars-rust to-mars-amber flex items-center justify-center text-white shadow-hud-glow">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-display font-bold text-sm text-white uppercase tracking-wider flex items-center gap-2">
              Contextual Mission Assistant
            </h3>
            <span className="font-mono text-[10px] text-slate-400">
              Interactive Ground Truth Reasoner // Scoped to Current Image
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Status Badge */}
          <div className={`px-2 py-0.5 rounded-full text-[10px] font-mono tracking-wider uppercase border flex items-center gap-1.5 ${
            isReasoningConfigured
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400'
              : 'bg-amber-950/60 border-amber-500/40 text-amber-300'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isReasoningConfigured ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            {isReasoningConfigured ? `META LLM (${reasoningModelName})` : 'DETERMINISTIC ASSISTANT'}
          </div>

          <button
            onClick={() => setShowHelpPanel(!showHelpPanel)}
            className={`p-1.5 rounded text-xs transition-all ${
              showHelpPanel ? 'bg-mars-rust text-white' : 'bg-mars-800 text-slate-400 hover:text-white'
            }`}
            title="Chatbot Architecture & Tool Capabilities"
          >
            <Info className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleResetConversation}
            className="p-1.5 rounded bg-mars-800 hover:bg-mars-750 text-slate-400 hover:text-white transition-all text-xs"
            title="Clear Chat History"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded bg-mars-800 hover:bg-mars-750 text-slate-400 hover:text-white transition-all text-xs"
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Help Panel Drawer */}
      {showHelpPanel && (
        <div className="p-4 bg-mars-950 border-b border-mars-800 font-mono text-xs space-y-3 animate-fadeIn text-slate-300">
          <div className="flex items-center justify-between text-mars-amber font-bold text-xs">
            <span className="uppercase">Mission Assistant Architecture & Boundaries</span>
            <button onClick={() => setShowHelpPanel(false)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
            <div className="p-2.5 rounded bg-mars-900 border border-mars-800 space-y-1">
              <strong className="text-white block uppercase">Reasoning Model:</strong>
              <span>Target: <code>{reasoningModelName}</code> (Meta OpenAI SDK API). When unconfigured, the deterministic query interpreter answers with 0% hallucination.</span>
            </div>
            <div className="p-2.5 rounded bg-mars-900 border border-mars-800 space-y-1">
              <strong className="text-white block uppercase">Controlled Tools:</strong>
              <span>Has read-only access to 6 sandboxed tools: <code>get_mission_summary</code>, <code>get_terrain_distribution</code>, <code>get_region_details</code>, <code>get_route_metrics</code>, <code>compare_routes</code>, <code>get_analysis_diagnostics</code>.</span>
            </div>
            <div className="p-2.5 rounded bg-mars-900 border border-mars-800 space-y-1">
              <strong className="text-white block uppercase">Safety & Security Guardrails:</strong>
              <span>Protected by autonomous planetary flight rules: internal credentials, API keys, and system secrets are strictly safeguarded. Unrelated topics are politely deflected.</span>
            </div>
            <div className="p-2.5 rounded bg-mars-900 border border-mars-800 space-y-1">
              <strong className="text-white block uppercase">Scientific Domain:</strong>
              <span>Answers RoverMind telemetry, A* routing, SAM 3.1 perception, and Mars / space science (Jezero geology, sols, Olympus Mons, rovers, and planetary dynamics).</span>
            </div>
          </div>
        </div>
      )}

      {isExpanded && (
        <div className="flex flex-col h-[480px]">
          {/* Message History Viewport */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 font-mono text-xs">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col justify-center items-center text-center p-6 space-y-4">
                <div className="w-10 h-10 rounded-full bg-mars-900 border border-mars-800 flex items-center justify-center text-mars-copper">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div className="max-w-sm space-y-1">
                  <p className="font-display font-bold text-white text-sm uppercase">Mission Assistant Ready</p>
                  <p className="text-[11px] text-slate-400">
                    Ask questions regarding terrain classifications, obstacle counts, route justifications, or simulate alternate traversal penalties.
                  </p>
                </div>

                {/* Suggested prompt chips */}
                <div className="flex flex-wrap gap-1.5 justify-center max-w-md pt-2">
                  {SUGGESTED_QUESTIONS.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(q)}
                      className="px-2.5 py-1 rounded bg-mars-900 hover:bg-mars-800 border border-mars-800 hover:border-mars-700 text-[10px] text-slate-300 transition-all text-left"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
                    {msg.role === 'user' ? (
                      <>
                        <span>OPERATOR</span>
                        <User className="w-3 h-3 text-mars-sky" />
                      </>
                    ) : (
                      <>
                        <Bot className="w-3 h-3 text-mars-copper" />
                        <span>MISSION INTELLIGENCE</span>
                        {msg.source_model && (
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono ${
                            msg.source_model.includes('DRY RUN')
                              ? 'bg-blue-950 text-blue-300 border border-blue-500/30'
                              : msg.source_model.includes('DISABLED')
                              ? 'bg-slate-900 text-slate-400 border border-slate-700'
                              : msg.is_ai_generated
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                              : 'bg-mars-800 text-amber-300 border border-amber-500/30'
                          }`}>
                            {msg.source_model}
                          </span>
                        )}
                      </>
                    )}
                    {msg.timestamp && <span>• {msg.timestamp}</span>}
                  </div>

                  <div
                    className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-mars-800 text-white border border-mars-700'
                        : 'bg-mars-900/90 text-slate-200 border border-mars-800 shadow-md'
                    }`}
                  >
                    {msg.content}

                    {/* Render tool execution badges & expandable details */}
                    {msg.tool_calls && msg.tool_calls.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-mars-800/80 space-y-1.5">
                        <span className="text-[9px] text-slate-500 uppercase tracking-widest block flex items-center gap-1">
                          <Wrench className="w-2.5 h-2.5 text-mars-amber" />
                          Backend Tools Executed:
                        </span>
                        <div className="space-y-1">
                          {msg.tool_calls.map((tc, tcIdx) => {
                            const toolKey = `${index}-${tcIdx}`;
                            const isToolExpanded = expandedToolIdx === toolKey;
                            return (
                              <div key={tcIdx} className="rounded bg-mars-950 border border-mars-800/80 text-[10px] font-mono overflow-hidden">
                                <button
                                  onClick={() => setExpandedToolIdx(isToolExpanded ? null : toolKey)}
                                  className="w-full px-2 py-1 flex items-center justify-between text-emerald-400 hover:bg-mars-900/80 transition-colors text-left"
                                >
                                  <span>✓ {tc.tool_name}</span>
                                  <span className="text-slate-500 text-[9px]">
                                    {isToolExpanded ? '▲ Hide Result' : '▼ Inspect Output'}
                                  </span>
                                </button>
                                {isToolExpanded && (
                                  <div className="p-2 border-t border-mars-800/60 bg-black/60 text-slate-300 max-h-40 overflow-y-auto text-[10px]">
                                    <span className="text-slate-500 block mb-1">Validated Result:</span>
                                    <pre className="whitespace-pre-wrap">{JSON.stringify(tc.result, null, 2)}</pre>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Active tool execution spinner */}
            {isLoading && activeTool && (
              <div className="flex items-center gap-2 p-2 rounded bg-mars-900/60 border border-mars-800/60 text-mars-amber text-xs animate-pulse">
                <Wrench className="w-3.5 h-3.5 animate-spin" />
                <span>{activeTool}</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-3 border-t border-mars-800 bg-mars-900/40">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about this route, obstacle counts, rover specs, or Mars science..."
                disabled={isLoading}
                className="flex-1 bg-mars-950 border border-mars-800 rounded px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-mars-rust transition-colors"
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading || !inputText.trim()}
                className="btn-primary p-2 text-xs flex items-center justify-center shrink-0 disabled:opacity-40"
                title="Send Message"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

