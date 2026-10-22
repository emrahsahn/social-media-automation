import { NextResponse } from 'next/server';

export async function GET() {
  const hasOpenAi = Boolean(process.env.OPENAI_API_KEY && process.env.OPENAI_API_KEY.trim());
  const hasAnthropic = Boolean(process.env.ANTHROPIC_API_KEY && process.env.ANTHROPIC_API_KEY.trim());

  const formats = [
    { key: 'post_4x5', label: 'Gönderi (4:5)', dimensions: '1080 x 1350 px', desc: 'En yüksek etkileşimli dikey feed' },
    { key: 'story_9x16', label: 'Hikaye / Reels (9:16)', dimensions: '1080 x 1920 px', desc: 'Tam ekran dikey format' },
    { key: 'square_1x1', label: 'Kare (1:1)', dimensions: '1080 x 1080 px', desc: 'Klasik Instagram kare formatı' },
  ];

  const styles = [
    { key: 'cinematic', label: 'Sinematik', desc: 'Dramatik ışık ve derinlik' },
    { key: 'minimalist', label: 'Minimalist', desc: 'Temiz, sade, şık zemin' },
    { key: 'neon_cyberpunk', label: 'Neon & Siber', desc: 'Canlı parlamalar ve kontrast' },
    { key: 'photorealistic', label: 'Foto-Gerçekçi', desc: 'Doğal dokular ve gerçekçilik' },
    { key: '3d_render', label: '3D Render', desc: 'Yumuşak gölgeli 3D öğeler' },
    { key: 'vintage_retro', label: 'Retro / Analog', desc: 'Sıcak tonlar, film greni' },
  ];

  const brand = {
    font: 'Poppins',
    text_color: '#FFFFFF',
    strip_color: '#000000',
    max_chars: 60,
    max_lines: 3,
  };

  return NextResponse.json({
    app_name: 'Sosyal Medya Otomasyon',
    version: '2.0.0 (Next.js)',
    providers: {
      openai: hasOpenAi,
      anthropic: hasAnthropic,
    },
    default_provider: hasOpenAi ? 'openai' : 'mock',
    formats,
    styles,
    brand,
  });
}
