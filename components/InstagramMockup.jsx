'use client';

import React, { useRef, useEffect, useState } from 'react';
import {
  Heart,
  MessageCircle,
  Send,
  Bookmark,
  Download,
  Copy,
  Check,
  MoreHorizontal,
} from 'lucide-react';
import confetti from 'canvas-confetti';

export default function InstagramMockup({
  currentPost,
  posts,
  currentIndex,
  onSelectIndex,
  format,
  overlayText,
  textColor,
  logoDataUrl,
}) {
  const canvasRef = useRef(null);
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(1428);

  // HTML5 Canvas üzerine profesyonel metin bindirme ve görsel oluşturma
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !currentPost) return;
    const ctx = canvas.getContext('2d');

    // Hedef boyutlar (Instagram 4:5 = 1080x1350, 9:16 = 1080x1920, 1:1 = 1080x1080)
    let w = 1080;
    let h = format === 'story_9x16' ? 1920 : format === 'square_1x1' ? 1080 : 1350;
    canvas.width = w;
    canvas.height = h;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = currentPost.image_url;

    img.onload = () => {
      // 1. Arka plan görseli çiz
      ctx.drawImage(img, 0, 0, w, h);

      // 2. Alt kısma okunabilirlik için koyu dikey gradient şerit
      const gradientHeight = h * 0.38;
      const gradient = ctx.createLinearGradient(0, h - gradientHeight, 0, h);
      gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
      gradient.addColorStop(0.3, 'rgba(0, 0, 0, 0.45)');
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0.88)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, h - gradientHeight, w, gradientHeight);

      // 3. Logo varsa bindir
      if (logoDataUrl) {
        const logo = new Image();
        logo.src = logoDataUrl;
        logo.onload = () => {
          const logoScale = 0.16;
          const logoW = w * logoScale;
          const logoH = (logo.height / logo.width) * logoW;
          ctx.drawImage(logo, w - logoW - 50, 50, logoW, logoH);
        };
      }

      // 4. Metin Bindirme (Word-wrap & auto-shrink)
      const text = (overlayText || currentPost.overlay_text || '').toUpperCase().trim();
      if (text) {
        ctx.fillStyle = textColor || '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
        ctx.shadowBlur = 12;

        let fontSize = Math.round(w * 0.055); // 1080px için ~60px
        ctx.font = `800 ${fontSize}px "Outfit", "Poppins", sans-serif`;

        // Satırlara böl
        const words = text.split(' ');
        const lines = [];
        let currentLine = words[0] || '';
        const maxLineWidth = w * 0.86;

        for (let i = 1; i < words.length; i++) {
          const testLine = `${currentLine} ${words[i]}`;
          if (ctx.measureText(testLine).width <= maxLineWidth) {
            currentLine = testLine;
          } else {
            lines.push(currentLine);
            currentLine = words[i];
          }
        }
        if (currentLine) lines.push(currentLine);

        // Satır sayısı fazlaysa puntoyu otomatik küçült
        if (lines.length > 3) {
          fontSize = Math.round(fontSize * 0.82);
          ctx.font = `800 ${fontSize}px "Outfit", "Poppins", sans-serif`;
        }

        const lineHeight = fontSize * 1.25;
        const startY = h - (h * 0.12) - ((lines.length - 1) * lineHeight);

        lines.forEach((line, idx) => {
          ctx.fillText(line, w / 2, startY + (idx * lineHeight));
        });
      }
    };
  }, [currentPost, format, overlayText, textColor, logoDataUrl]);

  // HD Görsel İndirme
  const handleDownloadImage = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `instagram-${format}-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    confetti({ particleCount: 40, spread: 60, origin: { y: 0.85 } });
  };

  // Caption Kopyalama
  const handleCopyCaption = () => {
    if (!currentPost) return;
    const fullText = `${currentPost.caption}\n\n${(currentPost.hashtags || []).join(' ')}`;
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    confetti({ particleCount: 50, spread: 70, origin: { y: 0.8 } });
    setTimeout(() => setCopied(false), 2200);
  };

  const handleToggleLike = () => {
    setLiked(!liked);
    setLikeCount(prev => (liked ? prev - 1 : prev + 1));
  };

  if (!currentPost) {
    return (
      <div className="stage-panel">
        <div className="phone-mockup">
          <div className="phone-screen" style={{ minHeight: '580px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', textAlign: 'center' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Sol panelden bir konu girin ve <strong>"GÖNDERİ PAKETİ ÜRET"</strong> butonuna basın.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const formatClass =
    format === 'story_9x16'
      ? 'story-9x16'
      : format === 'square_1x1'
      ? 'square-1x1'
      : 'post-4x5';

  return (
    <div className="stage-panel">
      {/* Varyasyon Sekmeleri */}
      {posts && posts.length > 1 && (
        <div className="variation-tabs">
          {posts.map((_, idx) => (
            <button
              key={idx}
              className={`tab-btn ${currentIndex === idx ? 'active' : ''}`}
              onClick={() => onSelectIndex(idx)}
            >
              Varyasyon {idx + 1}
            </button>
          ))}
        </div>
      )}

      {/* Gerçekçi Instagram Telefon Çerçevesi */}
      <div className="phone-mockup">
        <div className="phone-screen">
          {/* Dynamic Island */}
          <div className="phone-dynamic-island">
            <div className="camera-lens" />
          </div>

          {/* Instagram Post Üst Başlık */}
          <div className="insta-header">
            <div className="insta-profile">
              <div className="insta-avatar">
                <img
                  src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80"
                  alt="Avatar"
                />
              </div>
              <span className="insta-name">marka.ajansi</span>
            </div>
            <MoreHorizontal size={18} color="#a1a1aa" style={{ cursor: 'pointer' }} />
          </div>

          {/* Medya / Tuval Alanı */}
          <div className={`insta-media-box ${formatClass}`}>
            <canvas ref={canvasRef} className="canvas-preview" />
          </div>

          {/* Instagram Etkileşim Butonları */}
          <div className="insta-actions-bar">
            <div className="insta-left-actions">
              <Heart
                size={22}
                fill={liked ? '#ef4444' : 'none'}
                color={liked ? '#ef4444' : '#ffffff'}
                onClick={handleToggleLike}
                style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
              />
              <MessageCircle size={22} style={{ cursor: 'pointer' }} />
              <Send size={22} style={{ cursor: 'pointer' }} />
            </div>
            <Bookmark size={22} style={{ cursor: 'pointer' }} />
          </div>

          {/* Beğeni Sayısı & Açıklama */}
          <div className="insta-caption-area">
            <div style={{ fontWeight: 700, marginBottom: '4px' }}>
              {likeCount.toLocaleString('tr-TR')} beğenme
            </div>
            <div>
              <strong>marka.ajansi</strong>
              {currentPost.caption}
            </div>
            {currentPost.hashtags && currentPost.hashtags.length > 0 && (
              <div className="hashtags-block">
                {currentPost.hashtags.join(' ')}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Çıktı Butonları */}
      <div className="stage-actions">
        <button
          className="action-btn primary"
          onClick={handleDownloadImage}
          id="btnDownloadHd"
          title="Yüksek çözünürlüklü 1080px görseli indir"
        >
          <Download size={18} />
          Görseli İndir (HD PNG)
        </button>

        <button
          className="action-btn"
          onClick={handleCopyCaption}
          id="btnCopyCaption"
          title="Açıklama ve hashtag'leri panoya kopyala"
        >
          {copied ? <Check size={18} color="#10b981" /> : <Copy size={18} />}
          {copied ? 'Kopyalandı!' : 'Metin & Hashtag Kopyala'}
        </button>
      </div>
    </div>
  );
}
