'use client';

import React from 'react';
import { Sparkles, Wand2, RefreshCw, Image as ImageIcon } from 'lucide-react';

const QUICK_TOPICS = [
  'Yapay Zeka ve Gelecek',
  'Minimalist Yaşam Tarzı',
  'Girişimcilik ve Başarı',
  'Zaman Yönetimi İpuçları',
  'Siber Güvenlik Farkındalığı',
];

export default function GeneratorForm({
  formData,
  setFormData,
  onSubmit,
  loading,
}) {
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleLogoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        handleChange('logoDataUrl', event.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="sidebar-panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">İçerik Stüdyosu</h2>
          <p className="panel-subtitle">Yapay zeka ile görsel, metin ve tuval üretimi</p>
        </div>
      </div>

      {/* Konu Girdisi */}
      <div className="form-group">
        <label className="form-label" htmlFor="inputTopic">
          Konu / Tema
          <span className="form-label-desc">Türkçe veya İngilizce</span>
        </label>
        <textarea
          id="inputTopic"
          className="form-textarea"
          rows={3}
          placeholder="Örn: 2026 yılında üretkenliği artıran 5 dijital alışkanlık..."
          value={formData.topic}
          onChange={(e) => handleChange('topic', e.target.value)}
        />
        {/* Hızlı Konu Önerileri */}
        <div className="quick-topics">
          {QUICK_TOPICS.map((topic, idx) => (
            <button
              key={idx}
              type="button"
              className="topic-chip"
              onClick={() => handleChange('topic', topic)}
            >
              {topic}
            </button>
          ))}
        </div>
      </div>

      {/* Format Seçimi */}
      <div className="form-group">
        <label className="form-label">
          Format
          <span className="form-label-desc">Instagram hedef boyutu</span>
        </label>
        <div className="pill-grid">
          <div
            className={`pill-item ${formData.format === 'post_4x5' ? 'active' : ''}`}
            onClick={() => handleChange('format', 'post_4x5')}
            id="formatPost4x5"
          >
            <span>Gönderi</span>
            <span style={{ fontSize: '0.68rem', opacity: 0.8 }}>4:5 (1080p)</span>
          </div>
          <div
            className={`pill-item ${formData.format === 'story_9x16' ? 'active' : ''}`}
            onClick={() => handleChange('format', 'story_9x16')}
            id="formatStory9x16"
          >
            <span>Hikaye / Reels</span>
            <span style={{ fontSize: '0.68rem', opacity: 0.8 }}>9:16 (Dikey)</span>
          </div>
          <div
            className={`pill-item ${formData.format === 'square_1x1' ? 'active' : ''}`}
            onClick={() => handleChange('format', 'square_1x1')}
            id="formatSquare1x1"
          >
            <span>Kare</span>
            <span style={{ fontSize: '0.68rem', opacity: 0.8 }}>1:1 (Klasik)</span>
          </div>
        </div>
      </div>

      {/* Görsel Stili */}
      <div className="form-group">
        <label className="form-label">Görsel Stili</label>
        <div className="pill-grid">
          {[
            { key: 'cinematic', label: 'Sinematik' },
            { key: 'minimalist', label: 'Minimalist' },
            { key: 'neon_cyberpunk', label: 'Neon & Siber' },
            { key: 'photorealistic', label: 'Foto-Gerçek' },
          ].map(style => (
            <div
              key={style.key}
              className={`pill-item ${formData.style === style.key ? 'active' : ''}`}
              onClick={() => handleChange('style', style.key)}
            >
              {style.label}
            </div>
          ))}
        </div>
      </div>

      {/* Sayı & Kalite */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Varyasyon Sayısı</label>
          <div className="pill-grid-4">
            {[1, 2, 3, 4].map(num => (
              <div
                key={num}
                className={`pill-item ${formData.imageCount === num ? 'active' : ''}`}
                onClick={() => handleChange('imageCount', num)}
              >
                {num}
              </div>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">DALL-E Kalitesi</label>
          <div className="pill-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div
              className={`pill-item ${formData.quality === 'standard' ? 'active' : ''}`}
              onClick={() => handleChange('quality', 'standard')}
            >
              Standart
            </div>
            <div
              className={`pill-item ${formData.quality === 'hd' ? 'active' : ''}`}
              onClick={() => handleChange('quality', 'hd')}
            >
              HD (Detaylı)
            </div>
          </div>
        </div>
      </div>

      {/* Metin Bindirme (Overlay) */}
      <div className="form-group">
        <label className="form-label" htmlFor="inputOverlayText">
          Görsel Üstü Başlık (Canlı Önizleme)
          <span className="form-label-desc">Görselin altına basılır</span>
        </label>
        <input
          id="inputOverlayText"
          type="text"
          className="form-textarea"
          style={{ minHeight: 'unset', height: '42px' }}
          placeholder="Boş bırakırsanız konudan otomatik üretilir"
          value={formData.overlayText}
          onChange={(e) => handleChange('overlayText', e.target.value)}
        />
      </div>

      {/* Logo ve Renk Seçenekleri */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Metin Rengi</label>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              type="color"
              value={formData.textColor}
              onChange={(e) => handleChange('textColor', e.target.value)}
              style={{
                width: '38px',
                height: '38px',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                background: 'transparent',
              }}
            />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {formData.textColor}
            </span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Marka Logosu</label>
          <label
            className="action-btn"
            style={{ width: '100%', justifyContent: 'center', padding: '0.55rem' }}
          >
            <ImageIcon size={16} />
            {formData.logoDataUrl ? 'Logo Değiştir' : 'PNG Logo Ekle'}
            <input
              type="file"
              accept="image/png,image/svg+xml,image/jpeg"
              style={{ display: 'none' }}
              onChange={handleLogoUpload}
            />
          </label>
        </div>
      </div>

      {/* Mock Modu Seçeneği */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 0' }}>
        <input
          type="checkbox"
          id="checkMock"
          checked={formData.mock}
          onChange={(e) => handleChange('mock', e.target.checked)}
          style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#ffffff' }}
        />
        <label htmlFor="checkMock" style={{ fontSize: '0.82rem', cursor: 'pointer', color: 'var(--text-muted)' }}>
          Hızlı Mock Modu (API Harcaması Yapmadan Test Et)
        </label>
      </div>

      {/* Üretim Butonu */}
      <button
        className="submit-btn"
        onClick={onSubmit}
        disabled={loading || !formData.topic.trim()}
        id="btnGeneratePost"
      >
        {loading ? (
          <>
            <RefreshCw size={20} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} />
            İçerik Paketi Üretiliyor...
          </>
        ) : (
          <>
            <Wand2 size={20} />
            GÖNDERİ PAKETİ ÜRET
          </>
        )}
      </button>

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
