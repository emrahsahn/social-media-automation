'use client';

import React, { useState } from 'react';
import { X, Layers, Play, CheckCircle2 } from 'lucide-react';

export default function BatchModal({ isOpen, onClose, onRunBatch, isRunning, progress }) {
  const [batchText, setBatchText] = useState(
    'Yapay Zeka ve Yazılım Geliştirme\nMinimalist Yaşamın Püf Noktaları\nZaman Yönetimi Teknikleri'
  );

  if (!isOpen) return null;

  const handleStart = () => {
    const topics = batchText
      .split('\n')
      .map(t => t.trim())
      .filter(t => t.length > 2);
    if (topics.length > 0) {
      onRunBatch(topics);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers size={22} color="#ffffff" />
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800 }}>Toplu İçerik Üretimi (Batch)</h3>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Her satıra bir konu gelecek şekilde konularınızı girin. Sistem sırayla her biri için görsel, metin ve hashtag paketi oluşturacaktır.
        </p>

        <textarea
          className="form-textarea"
          rows={6}
          value={batchText}
          disabled={isRunning}
          onChange={e => setBatchText(e.target.value)}
          placeholder="Her satıra bir konu yazın..."
        />

        {isRunning && (
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
              <span>Üretim Durumu</span>
              <strong>%{progress}</strong>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'var(--bg-elevated)', borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${progress}%`,
                  height: '100%',
                  background: 'var(--insta-gradient)',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '1.5rem' }}>
          <button className="action-btn" onClick={onClose} disabled={isRunning}>
            Kapat
          </button>
          <button className="action-btn primary" onClick={handleStart} disabled={isRunning || !batchText.trim()}>
            {isRunning ? (
              'İşleniyor...'
            ) : (
              <>
                <Play size={16} />
                Toplu Üretimi Başlat
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
