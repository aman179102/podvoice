from __future__ import annotations

import base64
import html
import tempfile
import threading
from pathlib import Path

import yaml
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, Response

from .audio import build_podcast
from .parser import parse_markdown_script
from .tts import XTTSVoiceEngine
from .utils import ModelLoadError, PodvoiceError, ScriptParseError, SynthesisError, Segment


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0a0a0f;
      --bg-secondary: #12121a;
      --bg-tertiary: #1a1a25;
      --bg-elevated: #252535;
      --border-subtle: #2a2a3a;
      --border-default: #3a3a4f;
      --border-hover: #4a4a5f;
      --text-primary: #fafafa;
      --text-secondary: #a1a1aa;
      --text-muted: #71717a;
      --accent-primary: #6366f1;
      --accent-hover: #818cf8;
      --accent-glow: rgba(99, 102, 241, 0.3);
      --success: #22c55e;
      --warning: #f59e0b;
      --error: #ef4444;
      --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
      --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.5);
      --shadow-glow: 0 0 20px var(--accent-glow);
      --radius-sm: 8px;
      --radius-md: 12px;
      --radius-lg: 16px;
      --radius-xl: 24px;
      --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
      --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
      --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body {{ 
      height: 100%; 
      overflow: hidden;
    }}

    body {{ 
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
      background: var(--bg-primary); 
      color: var(--text-primary); 
      font-size: 14px;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}

    /* Scrollbar Styling */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ 
      background: var(--border-default); 
      border-radius: 3px; 
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--border-hover); }}

    /* App Header */
    .app-header {{ 
      height: 64px; 
      background: var(--bg-secondary); 
      border-bottom: 1px solid var(--border-subtle); 
      display: flex; 
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      flex-shrink: 0;
      position: relative;
      z-index: 100;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    /* Hamburger Menu Button */
    .hamburger-btn {{
      display: none;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background: var(--bg-tertiary);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.2s ease;
      padding: 0;
    }}

    .hamburger-btn:hover {{
      background: var(--bg-elevated);
      border-color: var(--border-hover);
      transform: scale(1.05);
    }}

    .hamburger-btn:active {{
      transform: scale(0.95);
    }}

    .hamburger-btn svg {{
      width: 20px;
      height: 20px;
    }}

    .brand {{ 
      display: flex; 
      align-items: center; 
      gap: 12px;
      text-decoration: none;
    }}

    .brand-icon {{ 
      width: 36px; 
      height: 36px; 
      background: linear-gradient(135deg, var(--accent-primary), #8b5cf6);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      box-shadow: var(--shadow-md);
    }}

    .brand-text {{ 
      font-weight: 800; 
      font-size: 1.25rem; 
      letter-spacing: -0.02em;
      color: var(--text-primary);
      background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}

    .nav-tabs {{ 
      display: flex; 
      gap: 4px;
      background: var(--bg-tertiary);
      padding: 4px;
      border-radius: var(--radius-md);
    }}

    .nav-tab {{ 
      padding: 8px 20px; 
      border-radius: var(--radius-sm);
      text-decoration: none;
      color: var(--text-secondary);
      font-weight: 500;
      font-size: 0.875rem;
      transition: all var(--transition-fast);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .nav-tab:hover {{ 
      color: var(--text-primary);
      background: var(--bg-elevated);
    }}

    .nav-tab.active {{ 
      color: var(--text-primary);
      background: var(--bg-elevated);
      box-shadow: var(--shadow-sm);
    }}

    /* App Container */
    .app-container {{ 
      display: flex; 
      height: calc(100vh - 64px);
      overflow: hidden;
    }}

    /* Sidebar */
    .sidebar {{ 
      width: 300px; 
      background: var(--bg-secondary); 
      border-right: 1px solid var(--border-subtle);
      display: flex; 
      flex-direction: column;
      flex-shrink: 0;
    }}

    .sidebar-header {{ 
      padding: 20px 20px 12px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .sidebar-title {{ 
      font-size: 0.75rem; 
      font-weight: 700; 
      text-transform: uppercase; 
      letter-spacing: 0.1em;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .sidebar-title svg {{ width: 14px; height: 14px; }}

    .voice-list {{ 
      flex: 1; 
      overflow-y: auto;
      padding: 8px;
    }}

    .voice-item {{ 
      padding: 12px; 
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all var(--transition-fast);
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 4px;
      border: 1px solid transparent;
    }}

    .voice-item:hover {{ 
      background: var(--bg-tertiary);
      border-color: var(--border-default);
    }}

    .voice-item.selected {{ 
      background: var(--bg-elevated);
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }}

    .voice-item.playing {{ 
      background: var(--bg-elevated);
      border-color: var(--success);
    }}

    .voice-avatar {{ 
      width: 40px; 
      height: 40px; 
      border-radius: 50%;
      background: linear-gradient(135deg, var(--accent-primary), #8b5cf6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 0.875rem;
      color: white;
      flex-shrink: 0;
      position: relative;
    }}

    .voice-avatar::after {{
      content: '';
      position: absolute;
      inset: -2px;
      border-radius: 50%;
      border: 2px solid transparent;
      transition: border-color var(--transition-fast);
    }}

    .voice-item.selected .voice-avatar::after {{
      border-color: var(--accent-primary);
    }}

    .voice-info {{ flex: 1; min-width: 0; }}

    .voice-name {{ 
      font-weight: 600; 
      font-size: 0.9375rem;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .voice-id {{ 
      font-size: 0.75rem; 
      color: var(--text-muted);
      font-family: 'SF Mono', Monaco, monospace;
      margin-top: 2px;
    }}

    .voice-play-icon {{ 
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--bg-elevated);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: all var(--transition-fast);
      flex-shrink: 0;
    }}

    .voice-item:hover .voice-play-icon,
    .voice-item.playing .voice-play-icon {{ opacity: 1; }}

    .voice-item.playing .voice-play-icon {{ 
      background: var(--success);
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0%, 100% {{ transform: scale(1); }}
      50% {{ transform: scale(1.05); }}
    }}

    /* Main Content */
    .main-content {{ 
      flex: 1; 
      overflow-y: auto;
      padding: 32px;
      background: var(--bg-primary);
    }}

    .content-wrapper {{
      max-width: 800px;
      margin: 0 auto;
    }}

    /* Cards */
    .pod-card {{ 
      background: var(--bg-secondary); 
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 28px;
      margin-bottom: 24px;
      transition: all var(--transition-base);
    }}

    .pod-card:hover {{ 
      border-color: var(--border-default);
      box-shadow: var(--shadow-md);
    }}

    .card-header {{ 
      display: flex; 
      justify-content: space-between; 
      align-items: flex-start;
      margin-bottom: 24px;
    }}

    .card-title {{ 
      font-size: 1.25rem; 
      font-weight: 700;
      color: var(--text-primary);
      margin: 0;
    }}

    .card-subtitle {{ 
      font-size: 0.875rem;
      color: var(--text-secondary);
      margin-top: 4px;
    }}

    /* Status Badge */
    .status-badge {{ 
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: var(--bg-tertiary);
      color: var(--text-secondary);
      border: 1px solid var(--border-default);
      transition: all var(--transition-fast);
    }}

    .status-badge.active {{ 
      background: rgba(99, 102, 241, 0.15);
      color: var(--accent-primary);
      border-color: var(--accent-primary);
    }}

    .status-badge::before {{
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }}

    /* Form Elements */
    .form-group {{ margin-bottom: 20px; }}

    .form-label {{ 
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .form-control,
    .form-select {{ 
      background: var(--bg-tertiary);
      border: 1px solid var(--border-default);
      color: var(--text-primary);
      padding: 14px 16px;
      border-radius: var(--radius-md);
      font-size: 0.9375rem;
      width: 100%;
      transition: all var(--transition-fast);
      font-family: inherit;
    }}

    .form-control::placeholder {{ color: var(--text-muted); }}

    .form-control:hover,
    .form-select:hover {{ border-color: var(--border-hover); }}

    .form-control:focus,
    .form-select:focus {{ 
      outline: none;
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px var(--accent-glow);
      background: var(--bg-secondary);
    }}

    textarea.form-control {{ 
      min-height: 140px; 
      resize: vertical;
      line-height: 1.7;
    }}

    textarea.form-control.markdown-editor {{
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 0.875rem;
      line-height: 1.8;
    }}

    /* Buttons */
    .pod-btn {{ 
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 24px;
      border-radius: var(--radius-md);
      font-weight: 600;
      font-size: 0.9375rem;
      border: none;
      cursor: pointer;
      transition: all var(--transition-fast);
      position: relative;
      overflow: hidden;
    }}

    .pod-btn::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, transparent 100%);
      opacity: 0;
      transition: opacity var(--transition-fast);
    }}

    .pod-btn:hover::before {{ opacity: 1; }}

    .pod-btn:active {{ transform: translateY(1px); }}

    .pod-btn:disabled {{ 
      opacity: 0.5; 
      cursor: not-allowed;
      transform: none;
    }}

    .pod-btn-primary {{ 
      background: linear-gradient(135deg, var(--accent-primary), #7c3aed);
      color: white;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }}

    .pod-btn-primary:hover:not(:disabled) {{ 
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
      transform: translateY(-1px);
    }}

    .pod-btn-secondary {{ 
      background: var(--bg-elevated);
      color: var(--text-primary);
      border: 1px solid var(--border-default);
    }}

    .pod-btn-secondary:hover:not(:disabled) {{ 
      background: var(--border-default);
      border-color: var(--border-hover);
    }}

    .pod-btn-sm {{ padding: 8px 16px; font-size: 0.875rem; }}

    /* Loading Spinner */
    .spinner {{ 
      width: 20px; 
      height: 20px; 
      border: 2px solid var(--border-default);
      border-top-color: var(--accent-primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}

    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

    .btn-content {{ 
      display: flex;
      align-items: center;
      gap: 8px;
      transition: opacity var(--transition-fast);
    }}

    .btn-loading .btn-content {{ opacity: 0.6; }}

    /* Custom Audio Player */
    .audio-player-container {{ 
      background: var(--bg-tertiary);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .play-btn {{ 
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--accent-primary);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      transition: all var(--transition-fast);
      flex-shrink: 0;
      position: relative;
    }}

    .play-btn:hover {{ 
      background: var(--accent-hover);
      transform: scale(1.05);
      box-shadow: var(--shadow-glow);
    }}

    .play-btn:active {{ transform: scale(0.95); }}

    .play-btn.playing {{ 
      background: var(--success);
    }}

    .play-icon,
    .pause-icon {{ 
      position: absolute;
      transition: all var(--transition-fast);
    }}

    .play-btn.playing .play-icon {{ 
      opacity: 0;
      transform: scale(0.8);
    }}

    .play-btn:not(.playing) .pause-icon {{ 
      opacity: 0;
      transform: scale(0.8);
    }}

    .audio-progress-wrapper {{ 
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .progress-bar-container {{ 
      height: 6px;
      background: var(--bg-elevated);
      border-radius: 3px;
      cursor: pointer;
      position: relative;
      overflow: hidden;
    }}

    .progress-bar {{ 
      height: 100%;
      background: linear-gradient(90deg, var(--accent-primary), var(--accent-hover));
      border-radius: 3px;
      width: 0%;
      transition: width 0.1s linear;
      position: relative;
    }}

    .progress-bar::after {{
      content: '';
      position: absolute;
      right: -8px;
      top: 50%;
      transform: translateY(-50%);
      width: 16px;
      height: 16px;
      background: white;
      border-radius: 50%;
      box-shadow: var(--shadow-md);
      opacity: 0;
      transition: opacity var(--transition-fast);
    }}

    .progress-bar-container:hover .progress-bar::after {{ opacity: 1; }}

    .audio-time {{ 
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
    }}

    .audio-actions {{ 
      display: flex;
      gap: 8px;
    }}

    .audio-action-btn {{ 
      width: 36px;
      height: 36px;
      border-radius: var(--radius-sm);
      background: var(--bg-elevated);
      border: 1px solid var(--border-default);
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all var(--transition-fast);
    }}

    .audio-action-btn:hover {{ 
      background: var(--border-default);
      color: var(--text-primary);
    }}

    /* Speaker Mapping Cards */
    .mapping-container {{ 
      display: grid;
      gap: 12px;
      margin-top: 12px;
    }}

    .mapping-card {{ 
      background: var(--bg-tertiary);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-md);
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 16px;
      transition: all var(--transition-fast);
    }}

    .mapping-card:hover {{ 
      border-color: var(--border-hover);
      background: var(--bg-elevated);
    }}

    .mapping-speaker {{ 
      min-width: 120px;
      padding: 8px 14px;
      background: var(--bg-elevated);
      border-radius: var(--radius-sm);
      font-weight: 600;
      font-size: 0.9375rem;
      color: var(--accent-primary);
      text-align: center;
      border: 1px solid var(--border-default);
    }}

    .mapping-arrow {{ 
      color: var(--text-muted);
      font-size: 1.25rem;
    }}

    .mapping-voice {{ 
      flex: 1;
    }}

    .mapping-voice select {{ 
      background: var(--bg-secondary);
    }}

    /* Toast Notifications */
    .toast-container {{ 
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 1000;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .toast {{ 
      background: var(--bg-secondary);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: var(--shadow-lg);
      animation: slideIn 0.3s ease;
      min-width: 300px;
    }}

    @keyframes slideIn {{
      from {{ transform: translateX(100%); opacity: 0; }}
      to {{ transform: translateX(0); opacity: 1; }}
    }}

    .toast.success {{ border-color: var(--success); }}
    .toast.error {{ border-color: var(--error); }}

    /* Hidden */
    .hidden {{ display: none !important; }}

    /* Animations */
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(10px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .animate-fade-in {{ animation: fadeIn 0.4s ease; }}

    /* Empty State */
    .empty-state {{ 
      text-align: center;
      padding: 48px 24px;
      color: var(--text-muted);
    }}

    .empty-state-icon {{ 
      font-size: 3rem;
      margin-bottom: 16px;
      opacity: 0.5;
    }}

    /* Mobile header with hamburger */
    .mobile-header {{
      display: none;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-subtle);
      margin: -24px -24px 20px -24px;
    }}
    
    .hamburger-btn {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--bg-tertiary);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      color: var(--text-primary);
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    
    .hamburger-btn:hover {{
      background: var(--bg-hover);
      border-color: var(--border-hover);
    }}
    
    .mobile-title {{
      font-weight: 600;
      font-size: 1rem;
      color: var(--text-primary);
    }}
    
    /* Sidebar close button */
    .sidebar-close {{
      display: none;
      background: none;
      border: none;
      color: var(--text-secondary);
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
      transition: all 0.2s ease;
    }}
    
    .sidebar-close:hover {{
      background: var(--bg-hover);
      color: var(--text-primary);
    }}
    
    /* Sidebar overlay with blur */
    .sidebar-overlay {{
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      z-index: 99;
      opacity: 0;
      transition: opacity 0.3s ease;
    }}
    
    .sidebar-overlay.active {{
      display: block;
      opacity: 1;
    }}

    /* Responsive */
    @media (max-width: 992px) {{
      .sidebar {{ width: 260px; }}
    }}

    @media (max-width: 768px) {{
      .hamburger-btn {{
        display: flex;
      }}
      
      .sidebar {{
        position: fixed;
        left: 0;
        top: 0;
        height: 100vh;
        z-index: 100;
        transform: translateX(-100%);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border-radius: 0;
        margin: 0;
        width: 280px;
        min-width: 280px;
        box-shadow: var(--shadow-lg);
      }}
      
      .sidebar.active {{
        transform: translateX(0);
      }}
      
      .sidebar-close {{
        display: block;
      }}
      
      .sidebar-overlay.active {{
        display: block;
        opacity: 1;
      }}
      
      .main-content {{
        padding: 20px;
        margin-left: 0;
      }}
      
      .pod-card {{ padding: 20px; }}
      
      /* Hide mobile header inside content since we have hamburger in top nav */
      .mobile-header {{
        display: none !important;
      }}
    }}
    
    @media (max-width: 576px) {{
      .app-header {{
        padding: 0 16px;
      }}
      
      .nav-tabs {{
        display: none;
      }}
    }}

    /* Icons */
    .icon {{ 
      width: 20px;
      height: 20px;
      display: inline-block;
      vertical-align: middle;
    }}
  </style>
</head>
<body>
<header class="app-header">
  <div class="header-left">
    <button class="hamburger-btn" onclick="toggleSidebar()" aria-label="Toggle voice gallery">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="12" x2="21" y2="12"/>
        <line x1="3" y1="18" x2="21" y2="18"/>
      </svg>
    </button>
    <a href="/" class="brand">
      <div class="brand-icon">🎙️</div>
      <span class="brand-text">PodVoice</span>
    </a>
  </div>
  <nav class="nav-tabs">
    <a href="/single" class="nav-tab {'active' if 'Single' in title else ''}">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v8M8 12h8"/>
      </svg>
      Single TTS
    </a>
    <a href="/multi" class="nav-tab {'active' if 'Multi' in title else ''}">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
      Multi TTS
    </a>
  </nav>
</header>
<div class="app-container">
  {body}
</div>
<div class="toast-container" id="toastContainer"></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""


def _nav() -> str:
    return ""


def _parse_mapping(text: str) -> dict[str, str]:
    """Parse mapping in either YAML or simple key=value lines."""

    text = (text or "").strip()
    if not text:
        return {}

    # Try YAML first.
    try:
        raw = yaml.safe_load(text)
        if isinstance(raw, dict):
            out: dict[str, str] = {}
            for k, v in raw.items():
                if v is None:
                    continue
                out[str(k).strip()] = str(v).strip()
            return out
    except Exception:
        pass

    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def run_studio(
    *,
    host: str,
    port: int,
    profiles_dir: Path,
    language: str,
    device: str,
    model_name: str,
) -> None:
    app = FastAPI(title="Podvoice Studio")

    try:
        engine = XTTSVoiceEngine(
            language=language,
            device=device,
            model_name=model_name,
        )
    except ModelLoadError as exc:
        raise PodvoiceError(str(exc)) from exc

    @app.get("/", response_class=HTMLResponse)
    def root() -> str:
        return single_page()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    _demo_cache: dict[str, bytes] = {}
    _demo_cache_lock = threading.Lock()

    def _display_voice_label(voice_id: str) -> str:
        if not voice_id:
            return "Default"
        if voice_id.startswith("p") and voice_id[1:].isdigit():
            return f"Speaker {voice_id[1:]}"
        if voice_id.isalpha():
            return voice_id.title()
        return voice_id

    def _resolve_voice(voice: str) -> tuple[str | None, bool]:
        voice = (voice or "").strip()
        if voice in {"", "default"}:
            if engine.available_speakers:
                return engine.available_speakers[0], False
            return None, True
        return voice, False

    def _speaker_options(selected: str | None = None) -> str:
        opts: list[str] = []

        if not engine.available_speakers:
            default_sel = " selected" if selected in {None, "", "default"} else ""
            opts.append(f"<option value='default'{default_sel}>default</option>")

        for s in engine.available_speakers:
            sel = " selected" if selected and selected == s else ""
            opts.append(f"<option value='{s}'{sel}>{_display_voice_label(s)}</option>")
        return "".join(opts)

    @app.get("/single", response_class=HTMLResponse)
    def single_page() -> str:
        voices = engine.available_speakers
        sidebar_items = []
        for v in voices:
            v_esc = html.escape(v).replace('\n', ' ').replace('\r', '')
            label = html.escape(_display_voice_label(v)).replace('\n', ' ').replace('\r', '')
            v_id = html.escape(base64.urlsafe_b64encode(v.encode("utf-8")).decode("ascii").replace('=', '').replace('+', '_').replace('/', '-'))
            # Get initials for avatar
            initials = label[:2].upper() if len(label) >= 2 else label[:1].upper()
            sidebar_items.append(f"""
<div class="voice-item" onclick="selectVoice('{v_esc}', '{v_id}', '{label}')" id="voice_{v_id}" data-voice="{v_esc}">
  <div class="voice-avatar">{initials}</div>
  <div class="voice-info">
    <div class="voice-name">{label}</div>
    <div class="voice-id">{v_esc}</div>
  </div>
  <div class="voice-play-icon">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z"/>
    </svg>
  </div>
</div>
""")
        
        sidebar_html = f"""
<div class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2a3 3 0 0 0-3 3v14a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v4a7 7 0 0 1-14 0v-4"/>
      </svg>
      Voice Gallery
    </div>
    <button class="sidebar-close" onclick="toggleSidebar()" aria-label="Close sidebar">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>
  </div>
  <div class="voice-list">
    {''.join(sidebar_items) if sidebar_items else '<div class="empty-state"><div class="empty-state-icon">🎙️</div>No voices available</div>'}
  </div>
</div>
<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
"""
        
        body = f"""
{sidebar_html}
<div class="main-content">
  <div class="content-wrapper">
    <!-- Main TTS Card -->
    <div class="pod-card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Single TTS</h2>
          <div class="card-subtitle">Generate high-quality speech from text</div>
        </div>
        <div id="selected_voice_badge" class="status-badge hidden">No voice selected</div>
      </div>
      
      <div class="form-group">
        <label class="form-label">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 7V4h3M4 17v3h3M20 7V4h-3M20 17v3h-3M9 9h6v6H9z"/>
          </svg>
          Text Content
        </label>
        <textarea id="tts_text" class="form-control" placeholder="Type something to convert to speech..."></textarea>
      </div>
      
      <div class="d-flex justify-content-end">
        <button class="pod-btn pod-btn-primary" id="generate_btn" onclick="generateTTS()" disabled>
          <span class="btn-content">
            <div id="synth_loading" class="spinner hidden"></div>
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Generate Audio
          </span>
        </button>
      </div>
    </div>

    <!-- Result Card with Custom Audio Player -->
    <div id="result_card" class="pod-card hidden animate-fade-in">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3 class="card-title" style="font-size: 1rem;">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18V5l12-2v13"/>
            <circle cx="6" cy="18" r="3"/>
            <circle cx="18" cy="16" r="3"/>
          </svg>
          Generated Audio
        </h3>
        <a id="download_link" class="pod-btn pod-btn-secondary pod-btn-sm" download="speech.wav">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download
        </a>
      </div>
      
      <!-- Custom Audio Player -->
      <div class="audio-player-container">
        <button class="play-btn" id="main_play_btn" onclick="toggleMainAudio()">
          <svg class="play-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg class="pause-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
          </svg>
        </button>
        
        <div class="audio-progress-wrapper">
          <div class="progress-bar-container" onclick="seekMainAudio(event)">
            <div class="progress-bar" id="main_progress_bar"></div>
          </div>
          <div class="audio-time">
            <span id="main_current_time">0:00</span>
            <span id="main_duration">0:00</span>
          </div>
        </div>
        
        <div class="audio-actions">
          <button class="audio-action-btn" onclick="changeVolume(-0.1)" title="Volume Down">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
            </svg>
          </button>
        </div>
      </div>
      
      <audio id="main_audio" class="hidden"></audio>
    </div>

    <!-- Preview Card -->
    <div class="pod-card">
      <div class="card-header" style="margin-bottom: 16px;">
        <div>
          <h3 class="card-title" style="font-size: 1rem;">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
            </svg>
            Voice Preview
          </h3>
          <div class="card-subtitle">Click any voice in the sidebar to preview</div>
        </div>
      </div>
      
      <div class="d-flex align-items-center gap-3">
        <button class="pod-btn pod-btn-secondary" id="preview_play_btn" onclick="togglePreview()" disabled>
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Play Preview
        </button>
        <div id="preview_loading" class="spinner hidden"></div>
        <div id="preview_voice_name" class="text-secondary">No voice selected</div>
      </div>
      <audio id="preview_audio" class="hidden"></audio>
    </div>
  </div>
</div>

<script>
  // Toggle sidebar for mobile
  function toggleSidebar() {{
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
  }}

  // Close sidebar on mobile (helper function)
  function closeSidebarIfMobile() {{
    if (window.innerWidth <= 768) {{
      toggleSidebar();
    }}
  }}

  let currentVoice = null;
  let currentVoiceId = null;
  let currentLabel = null;
  let mainAudioContext = null;

  // Toast notification helper
  function showToast(message, type = 'info') {{
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${{type}}`;
    toast.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        ${{type === 'success' ? '<path d="M20 6L9 17l-5-5"/>' : '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'}}
      </svg>
      <span>${{message}}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }}

  function formatTime(seconds) {{
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${{mins}}:${{secs.toString().padStart(2, '0')}}`;
  }}

  function selectVoice(voice, id, label) {{
    currentVoice = voice;
    currentVoiceId = id;
    currentLabel = label;
    
    // Update UI
    document.querySelectorAll('.voice-item').forEach(el => {{
      el.classList.remove('selected', 'playing');
    }});
    document.getElementById('voice_' + id).classList.add('selected');
    
    const badge = document.getElementById('selected_voice_badge');
    badge.textContent = label;
    badge.classList.remove('hidden');
    badge.classList.add('active');
    
    document.getElementById('generate_btn').disabled = false;
    document.getElementById('preview_play_btn').disabled = false;
    document.getElementById('preview_voice_name').textContent = label;

    // Close sidebar on mobile
    closeSidebarIfMobile();

    // Load and auto-play preview
    const audio = document.getElementById('preview_audio');
    const loading = document.getElementById('preview_loading');
    const voiceEl = document.getElementById('voice_' + id);
    
    loading.classList.remove('hidden');
    audio.src = '/demo_wav?voice=' + encodeURIComponent(voice);
    audio.oncanplaythrough = () => {{
      loading.classList.add('hidden');
      voiceEl.classList.add('playing');
      audio.play().catch(() => {{}});
    }};
    audio.onended = () => {{
      voiceEl.classList.remove('playing');
    }};
  }}

  function togglePreview() {{
    const audio = document.getElementById('preview_audio');
    const voiceEl = document.getElementById('voice_' + currentVoiceId);
    if (audio.paused) {{
      audio.play();
      voiceEl?.classList.add('playing');
    }} else {{
      audio.pause();
      voiceEl?.classList.remove('playing');
    }}
  }}

  // Main audio player controls
  function toggleMainAudio() {{
    const audio = document.getElementById('main_audio');
    const btn = document.getElementById('main_play_btn');
    
    if (audio.paused) {{
      audio.play();
      btn.classList.add('playing');
    }} else {{
      audio.pause();
      btn.classList.remove('playing');
    }}
  }}

  function seekMainAudio(event) {{
    const audio = document.getElementById('main_audio');
    const container = event.currentTarget;
    const rect = container.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audio.currentTime = percent * audio.duration;
  }}

  function changeVolume(delta) {{
    const audio = document.getElementById('main_audio');
    audio.volume = Math.max(0, Math.min(1, audio.volume + delta));
  }}

  function updateMainAudioProgress() {{
    const audio = document.getElementById('main_audio');
    const progressBar = document.getElementById('main_progress_bar');
    const currentTimeEl = document.getElementById('main_current_time');
    const durationEl = document.getElementById('main_duration');
    const btn = document.getElementById('main_play_btn');
    
    if (audio.duration) {{
      const percent = (audio.currentTime / audio.duration) * 100;
      progressBar.style.width = percent + '%';
      currentTimeEl.textContent = formatTime(audio.currentTime);
      durationEl.textContent = formatTime(audio.duration);
    }}
    
    if (audio.paused) {{
      btn.classList.remove('playing');
    }} else {{
      btn.classList.add('playing');
    }}
  }}

  // Attach main audio events
  document.getElementById('main_audio').addEventListener('timeupdate', updateMainAudioProgress);
  document.getElementById('main_audio').addEventListener('ended', () => {{
    document.getElementById('main_play_btn').classList.remove('playing');
  }});

  async function generateTTS() {{
    const text = document.getElementById('tts_text').value.trim();
    if (!text || !currentVoice) {{
      showToast('Please enter text and select a voice', 'error');
      return;
    }}

    const btn = document.getElementById('generate_btn');
    const loading = document.getElementById('synth_loading');
    const resultCard = document.getElementById('result_card');
    const audio = document.getElementById('main_audio');
    const dl = document.getElementById('download_link');

    btn.disabled = true;
    btn.classList.add('btn-loading');
    loading.classList.remove('hidden');

    try {{
      const formData = new FormData();
      formData.append('voice', currentVoice);
      formData.append('text', text);

      const resp = await fetch('/single/generate', {{
        method: 'POST',
        body: formData
      }});

      if (!resp.ok) {{
        const err = await resp.text();
        showToast('Error: ' + err, 'error');
        return;
      }}

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      
      audio.src = url;
      dl.href = url;
      dl.download = 'speech.wav';
      resultCard.classList.remove('hidden');
      
      // Auto-play
      audio.onloadedmetadata = () => {{
        audio.play();
        document.getElementById('main_play_btn').classList.add('playing');
        document.getElementById('main_duration').textContent = formatTime(audio.duration);
      }};
      
      showToast('Audio generated successfully!', 'success');
    }} catch (e) {{
      showToast('Request failed: ' + e, 'error');
    }} finally {{
      btn.disabled = false;
      btn.classList.remove('btn-loading');
      loading.classList.add('hidden');
    }}
  }}

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {{
    if (e.ctrlKey && e.key === 'Enter') {{
      generateTTS();
    }}
  }});
</script>
"""
        return _html_page("PodVoice Studio — Single", body)

    @app.get("/multi", response_class=HTMLResponse)
    def multi_page() -> str:
        voices = engine.available_speakers
        sidebar_items = []
        voice_options = []
        for v in voices:
            v_esc = html.escape(v).replace('\n', ' ').replace('\r', '')
            label = html.escape(_display_voice_label(v)).replace('\n', ' ').replace('\r', '')
            v_id = html.escape(base64.urlsafe_b64encode(v.encode("utf-8")).decode("ascii").replace('=', '').replace('+', '_').replace('/', '-'))
            initials = label[:2].upper() if len(label) >= 2 else label[:1].upper()
            sidebar_items.append(f"""
<div class="voice-item" onclick="selectVoicePreview('{v_esc}', '{v_id}', '{label}')" id="voice_{v_id}" data-voice="{v_esc}">
  <div class="voice-avatar">{initials}</div>
  <div class="voice-info">
    <div class="voice-name">{label}</div>
    <div class="voice-id">{v_esc}</div>
  </div>
  <div class="voice-play-icon">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z"/>
    </svg>
  </div>
</div>
""")
            voice_options.append(f"<option value='{v_esc}'>{label}</option>")
        
        sidebar_html = f"""
<div class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2a3 3 0 0 0-3 3v14a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v4a7 7 0 0 1-14 0v-4"/>
      </svg>
      Voice Gallery
    </div>
    <button class="sidebar-close" onclick="toggleSidebar()" aria-label="Close sidebar">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>
  </div>
  <div class="voice-list">
    {''.join(sidebar_items) if sidebar_items else '<div class="empty-state"><div class="empty-state-icon">🎙️</div>No voices available</div>'}
  </div>
</div>
<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
"""
        example_script = html.escape("""[Host | warm]
Welcome to PodVoice! This is a multi-speaker demo.

[Guest | upbeat]
You can write Markdown scripts with speaker tags like this.

[Host]
Each speaker gets their own voice. It's perfect for podcasts!""")
        fallback_voice = engine.available_speakers[0].replace('\n', ' ').replace('\r', '') if engine.available_speakers else "default"

        body = f"""
{sidebar_html}
<div class="main-content">
  <div class="content-wrapper">
    <!-- Mobile Header with Hamburger -->
    <div class="mobile-header">
      <button class="hamburger-btn" onclick="toggleSidebar()" aria-label="Open voice gallery">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
        <span>Voices</span>
      </button>
      <div class="mobile-title">PodVoice Multi</div>
    </div>

    <!-- Script Editor Card -->
    <div class="pod-card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Multi TTS Podcast</h2>
          <div class="card-subtitle">Create multi-speaker audio from Markdown</div>
        </div>
      </div>
      
      <div class="form-group">
        <label class="form-label">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <line x1="10" y1="9" x2="8" y2="9"/>
          </svg>
          Markdown Script
        </label>
        <textarea id="multi_script" class="form-control markdown-editor" placeholder="[Speaker | emotion] Your text here...">{example_script}</textarea>
        <div class="mt-2 text-secondary" style="font-size: 0.75rem;">
          <svg class="icon" style="width: 14px; height: 14px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4"/><path d="M12 8h.01"/>
          </svg>
          Format: <code>[Speaker | emotion]</code> followed by text. Emotion is optional.
        </div>
      </div>
    </div>

    <!-- Speaker Mapping Card -->
    <div class="pod-card">
      <div class="card-header">
        <div>
          <h3 class="card-title" style="font-size: 1rem;">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            Speaker Mapping
          </h3>
          <div class="card-subtitle">Assign voices to each speaker in your script</div>
        </div>
        <button class="pod-btn pod-btn-secondary pod-btn-sm" onclick="autoMapSpeakers()">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 3v18M3 12h18"/>
          </svg>
          Auto-Map
        </button>
      </div>
      
      <div id="mapping_container" class="mapping-container">
        <!-- Dynamic mapping cards will be inserted here -->
        <div class="empty-state" id="empty_mapping">
          <div class="empty-state-icon">🎭</div>
          <div>Enter a script above to see speaker mapping options</div>
        </div>
      </div>
      
      <!-- Hidden textarea for form submission -->
      <textarea id="multi_mapping" class="hidden"></textarea>
      
      <div class="d-flex justify-content-end mt-4">
        <button class="pod-btn pod-btn-primary" id="render_btn" onclick="renderPodcast()">
          <span class="btn-content">
            <div id="multi_loading" class="spinner hidden"></div>
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Render Podcast
          </span>
        </button>
      </div>
    </div>

    <!-- Result Card with Custom Audio Player -->
    <div id="multi_result_card" class="pod-card hidden animate-fade-in">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3 class="card-title" style="font-size: 1rem;">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18V5l12-2v13"/>
            <circle cx="6" cy="18" r="3"/>
            <circle cx="18" cy="16" r="3"/>
          </svg>
          Generated Podcast
        </h3>
        <a id="multi_download_link" class="pod-btn pod-btn-secondary pod-btn-sm" download="podcast.wav">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download
        </a>
      </div>
      
      <div class="audio-player-container">
        <button class="play-btn" id="multi_play_btn" onclick="toggleMultiAudio()">
          <svg class="play-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg class="pause-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
          </svg>
        </button>
        
        <div class="audio-progress-wrapper">
          <div class="progress-bar-container" onclick="seekMultiAudio(event)">
            <div class="progress-bar" id="multi_progress_bar"></div>
          </div>
          <div class="audio-time">
            <span id="multi_current_time">0:00</span>
            <span id="multi_duration">0:00</span>
          </div>
        </div>
      </div>
      
      <audio id="multi_audio" class="hidden"></audio>
    </div>

    <!-- Voice Preview Card -->
    <div class="pod-card">
      <div class="card-header" style="margin-bottom: 16px;">
        <div>
          <h3 class="card-title" style="font-size: 1rem;">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
            </svg>
            Quick Preview
          </h3>
          <div class="card-subtitle">Click any voice in the sidebar to preview</div>
        </div>
      </div>
      
      <div class="d-flex align-items-center gap-3">
        <button class="pod-btn pod-btn-secondary pod-btn-sm" id="preview_play_btn" onclick="togglePreview()" disabled>
          <svg class="icon play-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <svg class="icon pause-icon hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="4" width="4" height="16"/>
            <rect x="14" y="4" width="4" height="16"/>
          </svg>
          <span class="btn-text">Play</span>
        </button>
        <div id="preview_loading" class="spinner hidden"></div>
        <div id="preview_voice_name" class="text-secondary">No voice selected</div>
      </div>
      <audio id="preview_audio" class="hidden"></audio>
    </div>
  </div>
</div>

<script>
  function toggleSidebar() {{
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
  }}

  // Close sidebar on mobile (helper function)
  function closeSidebarIfMobile() {{
    if (window.innerWidth <= 768) {{
      toggleSidebar();
    }}
  }}

  const voiceOptions = `{''.join(voice_options)}`;
  const fallbackVoice = '{fallback_voice}';
  let currentVoice = null;
  let currentVoiceId = null;
  
  function showToast(message, type = 'info') {{
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${{type}}`;
    toast.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        ${{type === 'success' ? '<path d="M20 6L9 17l-5-5"/>' : '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'}}
      </svg>
      <span>${{message}}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }}

  function formatTime(seconds) {{
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${{mins}}:${{secs.toString().padStart(2, '0')}}`;
  }}

  function parseSpeakers(script) {{
    const lines = script.split('\\n');
    const speakers = new Set();
    for (const line of lines) {{
      const match = line.match(/^\\[([^\\]]+)\\]/);
      if (match) {{
        const speakerPart = match[1].split('|')[0].trim();
        speakers.add(speakerPart);
      }}
    }}
    return Array.from(speakers);
  }}

  function updateMappingUI() {{
    const script = document.getElementById('multi_script').value;
    const speakers = parseSpeakers(script);
    const container = document.getElementById('mapping_container');
    const emptyState = document.getElementById('empty_mapping');
    
    if (speakers.length === 0) {{
      container.innerHTML = `
        <div class="empty-state" id="empty_mapping">
          <div class="empty-state-icon">🎭</div>
          <div>Enter a script above to see speaker mapping options</div>
        </div>
      `;
      return;
    }}
    
    let html = '';
    speakers.forEach((speaker, index) => {{
      html += `
        <div class="mapping-card">
          <div class="mapping-speaker">${{speaker}}</div>
          <div class="mapping-arrow">→</div>
          <div class="mapping-voice">
            <select class="form-select speaker-voice-select" data-speaker="${{speaker}}">
              <option value="">Select voice...</option>
              ${{voiceOptions}}
            </select>
          </div>
        </div>
      `;
    }});
    
    container.innerHTML = html;
    
    // Auto-select voices
    speakers.forEach((speaker, index) => {{
      const selects = document.querySelectorAll('.speaker-voice-select');
      if (selects[index]) {{
        const options = selects[index].querySelectorAll('option');
        if (options[index + 1]) {{
          selects[index].selectedIndex = index + 1;
        }} else if (options[1]) {{
          selects[index].selectedIndex = 1;
        }}
      }}
    }});
    
    updateMappingTextarea();
  }}

  function autoMapSpeakers() {{
    updateMappingUI();
    showToast('Speakers auto-mapped to voices', 'success');
  }}

  function updateMappingTextarea() {{
    const selects = document.querySelectorAll('.speaker-voice-select');
    const mapping = [];
    selects.forEach(select => {{
      const speaker = select.dataset.speaker;
      const voice = select.value;
      if (voice) {{
        mapping.push(`${{speaker}}: ${{voice}}`);
      }}
    }});
    document.getElementById('multi_mapping').value = mapping.join('\\n');
  }}

  // Listen for script changes
  let debounceTimer;
  document.getElementById('multi_script').addEventListener('input', () => {{
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(updateMappingUI, 500);
  }});

  // Listen for mapping changes
  document.addEventListener('change', (e) => {{
    if (e.target.classList.contains('speaker-voice-select')) {{
      updateMappingTextarea();
    }}
  }});

  function selectVoicePreview(voice, id, label) {{
    console.log('selectVoicePreview called:', voice, id, label);
    
    if (!voice || !id) {{
      console.error('Invalid voice or id');
      return;
    }}
    
    currentVoice = voice;
    currentVoiceId = id;
    
    document.querySelectorAll('.voice-item').forEach(el => el.classList.remove('selected', 'playing'));
    
    const voiceEl = document.getElementById('voice_' + id);
    if (!voiceEl) {{
      console.error('Voice element not found: voice_' + id);
      return;
    }}
    
    voiceEl.classList.add('selected');
    
    // Close sidebar on mobile
    closeSidebarIfMobile();
    
    document.getElementById('preview_voice_name').textContent = label;
    document.getElementById('preview_play_btn').disabled = false;
    updatePreviewButtonState(false);

    const audio = document.getElementById('preview_audio');
    const loading = document.getElementById('preview_loading');
    
    loading.classList.remove('hidden');
    
    const url = '/demo_wav?voice=' + encodeURIComponent(voice);
    console.log('Loading audio from:', url);
    
    audio.src = url;
    
    audio.onerror = (e) => {{
      console.error('Audio error:', e);
      loading.classList.add('hidden');
      showToast('Failed to load voice preview', 'error');
    }};
    
    audio.oncanplaythrough = () => {{
      console.log('Audio ready to play');
      loading.classList.add('hidden');
      voiceEl.classList.add('playing');
      audio.play().catch(err => console.error('Play error:', err));
      updatePreviewButtonState(true);
    }};
    
    audio.onended = () => {{
      voiceEl.classList.remove('playing');
      updatePreviewButtonState(false);
    }};
    
    audio.onpause = () => {{
      updatePreviewButtonState(false);
    }};
    
    audio.onplay = () => {{
      updatePreviewButtonState(true);
    }};
  }}
  
  function updatePreviewButtonState(isPlaying) {{
    const btn = document.getElementById('preview_play_btn');
    const playIcon = btn.querySelector('.play-icon');
    const pauseIcon = btn.querySelector('.pause-icon');
    const btnText = btn.querySelector('.btn-text');
    
    if (isPlaying) {{
      playIcon.classList.add('hidden');
      pauseIcon.classList.remove('hidden');
      btnText.textContent = 'Pause';
    }} else {{
      playIcon.classList.remove('hidden');
      pauseIcon.classList.add('hidden');
      btnText.textContent = 'Play';
    }}
  }}

  function togglePreview() {{
    const audio = document.getElementById('preview_audio');
    const voiceEl = document.getElementById('voice_' + currentVoiceId);
    if (!audio.src) return;
    
    if (audio.paused) {{
      audio.play();
      voiceEl?.classList.add('playing');
    }} else {{
      audio.pause();
      voiceEl?.classList.remove('playing');
    }}
  }}

  // Multi audio player controls
  function toggleMultiAudio() {{
    const audio = document.getElementById('multi_audio');
    const btn = document.getElementById('multi_play_btn');
    
    if (audio.paused) {{
      audio.play();
      btn.classList.add('playing');
    }} else {{
      audio.pause();
      btn.classList.remove('playing');
    }}
  }}

  function seekMultiAudio(event) {{
    const audio = document.getElementById('multi_audio');
    const container = event.currentTarget;
    const rect = container.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audio.currentTime = percent * audio.duration;
  }}

  function updateMultiAudioProgress() {{
    const audio = document.getElementById('multi_audio');
    const progressBar = document.getElementById('multi_progress_bar');
    const currentTimeEl = document.getElementById('multi_current_time');
    const durationEl = document.getElementById('multi_duration');
    const btn = document.getElementById('multi_play_btn');
    
    if (audio.duration) {{
      const percent = (audio.currentTime / audio.duration) * 100;
      progressBar.style.width = percent + '%';
      currentTimeEl.textContent = formatTime(audio.currentTime);
      durationEl.textContent = formatTime(audio.duration);
    }}
    
    if (audio.paused) {{
      btn.classList.remove('playing');
    }} else {{
      btn.classList.add('playing');
    }}
  }}

  document.getElementById('multi_audio').addEventListener('timeupdate', updateMultiAudioProgress);
  document.getElementById('multi_audio').addEventListener('ended', () => {{
    document.getElementById('multi_play_btn').classList.remove('playing');
  }});

  async function renderPodcast() {{
    const script = document.getElementById('multi_script').value.trim();
    const mapping = document.getElementById('multi_mapping').value.trim();
    
    if (!script) {{
      showToast('Please enter a script', 'error');
      return;
    }}
    
    if (!mapping) {{
      showToast('Please map speakers to voices', 'error');
      return;
    }}

    const btn = document.getElementById('render_btn');
    const loading = document.getElementById('multi_loading');
    const resultCard = document.getElementById('multi_result_card');
    const audio = document.getElementById('multi_audio');
    const dl = document.getElementById('multi_download_link');

    btn.disabled = true;
    btn.classList.add('btn-loading');
    loading.classList.remove('hidden');

    try {{
      const formData = new FormData();
      formData.append('script', script);
      formData.append('mapping', mapping);

      const resp = await fetch('/multi/render', {{
        method: 'POST',
        body: formData
      }});

      if (!resp.ok) {{
        const err = await resp.text();
        showToast('Error: ' + err, 'error');
        return;
      }}

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      
      audio.src = url;
      dl.href = url;
      dl.download = 'podcast.wav';
      resultCard.classList.remove('hidden');
      
      audio.onloadedmetadata = () => {{
        audio.play();
        document.getElementById('multi_play_btn').classList.add('playing');
        document.getElementById('multi_duration').textContent = formatTime(audio.duration);
      }};
      
      showToast('Podcast rendered successfully!', 'success');
    }} catch (e) {{
      showToast('Request failed: ' + e, 'error');
    }} finally {{
      btn.disabled = false;
      btn.classList.remove('btn-loading');
      loading.classList.add('hidden');
    }}
  }}

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {{
    if (e.ctrlKey && e.key === 'Enter') {{
      renderPodcast();
    }}
  }});

  // Initial mapping
  updateMappingUI();
</script>
"""
        return _html_page("PodVoice Studio — Multi", body)

    @app.get("/demo_wav")
    def demo_wav(voice: str) -> Response:
        voice = (voice or "").strip()
        cache_key = voice or "__default__"
        with _demo_cache_lock:
            cached = _demo_cache.get(cache_key)
        if cached is not None:
            return Response(cached, media_type="audio/wav")

        seg = Segment(speaker="demo", emotion=None, text="Hello. This is a Podvoice built-in voice demo.")
        with tempfile.TemporaryDirectory(prefix="podvoice_demo_") as tmp:
            out = Path(tmp) / "demo.wav"
            try:
                builtin_speaker, use_default_voice = _resolve_voice(voice)
                engine.synthesize_to_path(
                    seg,
                    out,
                    builtin_speaker=builtin_speaker,
                    use_default_voice=use_default_voice,
                )
            except SynthesisError as exc:
                msg = str(exc)
                if "Voice file" in msg and "not found" in msg:
                    msg += "\n\nTip: This model may not expose built-in speakers on your system."
                return Response(msg, status_code=400, media_type="text/plain")
            data = out.read_bytes()

        with _demo_cache_lock:
            _demo_cache[cache_key] = data
        return Response(data, media_type="audio/wav")

    @app.post("/demo")
    def demo(voice: str = Form(...)) -> Response:
        voice = voice.strip()
        seg = Segment(speaker="demo", emotion=None, text="Hello. This is a Podvoice built-in voice demo.")
        with tempfile.TemporaryDirectory(prefix="podvoice_demo_") as tmp:
            out = Path(tmp) / "demo.wav"
            try:
                builtin_speaker, use_default_voice = _resolve_voice(voice)
                engine.synthesize_to_path(
                    seg,
                    out,
                    builtin_speaker=builtin_speaker,
                    use_default_voice=use_default_voice,
                )
            except SynthesisError as exc:
                msg = str(exc)
                if "Voice file" in msg and "not found" in msg:
                    msg += "\n\nTip: This model may not expose built-in speakers on your system. Use voice=default."
                return Response(msg, status_code=400, media_type="text/plain")

            audio_b64 = base64.b64encode(out.read_bytes()).decode("ascii")
            body = f"""
<h1>Podvoice Studio</h1>
{_nav()}

<div class='card'>
  <h3>Voice demo</h3>
  <div class='muted'>Voice: <code>{voice}</code></div>
  <div style='height:12px'></div>
  <audio controls autoplay style='width:100%'>
    <source src='data:audio/wav;base64,{audio_b64}' type='audio/wav' />
  </audio>
  <div style='height:10px'></div>
  <a class='btn' download='demo.wav' href='data:audio/wav;base64,{audio_b64}'>Download demo.wav</a>
</div>
"""
            return HTMLResponse(_html_page("Podvoice Studio — Demo", body))

    @app.post("/single/generate")
    def single_generate(
        voice: str = Form(...), 
        text: str = Form(...)
    ) -> Response:
        voice = voice.strip()
        text = text.strip()
        seg = Segment(speaker="single", emotion=None, text=text)
        with tempfile.TemporaryDirectory(prefix="podvoice_single_") as tmp:
            out = Path(tmp) / "single.wav"
            try:
                builtin_speaker, use_default_voice = _resolve_voice(voice)
                engine.synthesize_to_path(
                    seg,
                    out,
                    builtin_speaker=builtin_speaker,
                    use_default_voice=use_default_voice,
                )
            except SynthesisError as exc:
                msg = str(exc)
                if "Voice file" in msg and "not found" in msg:
                    msg += "\n\nTip: This model may not expose built-in speakers on your system. Use voice=default."
                return Response(msg, status_code=400, media_type="text/plain")

            return Response(out.read_bytes(), media_type="audio/wav")

    @app.post("/multi/render")
    def multi_render(
        script: str = Form(...), 
        mapping: str = Form(...)
    ) -> Response:
        script = script or ""
        mapping_dict = _parse_mapping(mapping)
        try:
            segments = parse_markdown_script(script, source="<studio>")
        except ScriptParseError as exc:
            return Response(str(exc), status_code=400, media_type="text/plain")

        with tempfile.TemporaryDirectory(prefix="podvoice_multi_") as tmp:
            tmp_dir = Path(tmp)
            paths: list[Path] = []
            for idx, seg in enumerate(segments):
                out = tmp_dir / f"seg_{idx:04d}.wav"
                voice = mapping_dict.get(seg.speaker)
                if not voice:
                    return Response(
                        f"Missing voice mapping for speaker '{seg.speaker}'.",
                        status_code=400,
                        media_type="text/plain",
                    )
                try:
                    builtin_speaker, use_default_voice = _resolve_voice(voice)
                    engine.synthesize_to_path(
                        seg,
                        out,
                        builtin_speaker=builtin_speaker,
                        use_default_voice=use_default_voice,
                    )
                except SynthesisError as exc:
                    msg = str(exc)
                    if "Voice file" in msg and "not found" in msg:
                        msg += "\n\nTip: This model may not expose built-in speakers on your system. Use voice=default."
                    return Response(msg, status_code=400, media_type="text/plain")
                paths.append(out)

            try:
                combined = build_podcast(paths)
            except PodvoiceError as exc:
                return Response(str(exc), status_code=400, media_type="text/plain")

            out_final = tmp_dir / "podcast.wav"
            combined.export(out_final, format="wav")
            
            return Response(out_final.read_bytes(), media_type="audio/wav")

    uvicorn.run(app, host=host, port=port, log_level="info")
