'use client';

import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import GeneratorForm from '../components/GeneratorForm';
import InstagramMockup from '../components/InstagramMockup';
import BatchModal from '../components/BatchModal';
import { SlidersHorizontal, Smartphone } from 'lucide-react';

export default function Home() {
  const [theme, setTheme] = useState('dark');
  const [totalCost, setTotalCost] = useState(0);
  const [isMock, setIsMock] = useState(true);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [activeMobileTab, setActiveMobileTab] = useState('form'); // 'form' | 'preview'

  // Form Durumu
  const [formData, setFormData] = useState({
    topic: 'Yapay Zeka ile Sosyal Medya Otomasyonu',
    imageCount: 2,
    format: 'post_4x5',
    style: 'cinematic',
    quality: 'standard',
    overlayText: 'YAPAY ZEKA İLE İÇERİK ÜRETİMİ',
    textColor: '#FFFFFF',
    logoDataUrl: null,
    mock: true,
  });

  // Üretilen Gönderiler
  const [posts, setPosts] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Toplu Üretim Durumu
  const [batchOpen, setBatchOpen] = useState(false);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState(0);

  // Tema Değiştirme
  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  // Toast Bildirimi
  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  // Sayfa açıldığında ilk önizlemeyi yükle
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        if (data.providers?.openai) {
          setIsMock(false);
          setFormData(prev => ({ ...prev, mock: false }));
        }
      })
      .catch(() => {});

    handleGenerate(true);
  }, []);

  const handleGenerate = async (isInitial = false) => {
    setLoading(true);
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: formData.topic,
          image_count: formData.imageCount,
          format: formData.format,
          style: formData.style,
          quality: formData.quality,
          overlay_text: formData.overlayText,
          mock: formData.mock,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'İçerik üretilirken hata oluştu.');
      }

      setPosts(data.posts || []);
      setCurrentIndex(0);
      setTotalCost(prev => prev + (data.cost_usd || 0));

      if (!isInitial) {
        showToast('🎉 Yeni Instagram gönderi paketi hazırlandı!');
        // Mobilde kullanıcı direkt önizlemeyi görsün diye önizleme sekmesine geç
        if (window.innerWidth < 1024) {
          setActiveMobileTab('preview');
        }
      }
    } catch (err) {
      showToast(`Hata: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Toplu Üretim
  const handleRunBatch = async (topics) => {
    setBatchRunning(true);
    setBatchProgress(10);
    const allGenerated = [];

    for (let i = 0; i < topics.length; i++) {
      const topic = topics[i];
      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic,
            image_count: 1,
            format: formData.format,
            style: formData.style,
            quality: formData.quality,
            overlay_text: topic.toUpperCase(),
            mock: formData.mock,
          }),
        });
        const data = await res.json();
        if (data.posts) {
          allGenerated.push(...data.posts);
          setTotalCost(prev => prev + (data.cost_usd || 0));
        }
      } catch (e) {
        console.error('Batch item error:', e);
      }
      setBatchProgress(Math.round(((i + 1) / topics.length) * 100));
    }

    if (allGenerated.length > 0) {
      setPosts(allGenerated);
      setCurrentIndex(0);
      showToast(`✅ ${allGenerated.length} adet gönderi başarıyla üretildi!`);
      if (window.innerWidth < 1024) {
        setActiveMobileTab('preview');
      }
    }
    setBatchRunning(false);
    setBatchOpen(false);
  };

  const currentPost = posts[currentIndex] || null;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        isMock={formData.mock}
        totalCost={totalCost}
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenBatch={() => setBatchOpen(true)}
      />

      {/* Mobil Sekme Değiştirici (Sadece mobil/tablette görünür) */}
      <div className="mobile-tabs-container">
        <button
          className={`mobile-tab-btn ${activeMobileTab === 'form' ? 'active' : ''}`}
          onClick={() => setActiveMobileTab('form')}
          id="btnTabForm"
        >
          <SlidersHorizontal size={16} />
          İçerik Stüdyosu
        </button>
        <button
          className={`mobile-tab-btn ${activeMobileTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveMobileTab('preview')}
          id="btnTabPreview"
        >
          <Smartphone size={16} />
          Canlı Önizleme {posts.length > 0 && `(${posts.length})`}
        </button>
      </div>

      <main className="main-container">
        {/* Sol Panel: İçerik Üretim Kontrolleri */}
        <div className={`panel-wrapper ${activeMobileTab !== 'form' ? 'mobile-hidden' : ''}`}>
          <GeneratorForm
            formData={formData}
            setFormData={setFormData}
            onSubmit={() => handleGenerate(false)}
            loading={loading}
          />
        </div>

        {/* Sağ Panel: Canlı Instagram Telefon & Çıktı Önizlemesi */}
        <div className={`panel-wrapper ${activeMobileTab !== 'preview' ? 'mobile-hidden' : ''}`}>
          <InstagramMockup
            currentPost={currentPost}
            posts={posts}
            currentIndex={currentIndex}
            onSelectIndex={setCurrentIndex}
            format={formData.format}
            overlayText={formData.overlayText}
            textColor={formData.textColor}
            logoDataUrl={formData.logoDataUrl}
          />
        </div>
      </main>

      {/* Toplu Üretim Penceresi */}
      <BatchModal
        isOpen={batchOpen}
        onClose={() => setBatchOpen(false)}
        onRunBatch={handleRunBatch}
        isRunning={batchRunning}
        progress={batchProgress}
      />

      {/* Toast Bildirimi */}
      {toast && <div className="toast-msg">{toast}</div>}
    </div>
  );
}
