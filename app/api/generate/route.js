import { NextResponse } from 'next/server';

// Mock konular için tema odaklı zengin görsel koleksiyonu
const MOCK_PRESET_IMAGES = {
  cinematic: [
    'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1080&q=85',
  ],
  minimalist: [
    'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1080&q=85',
  ],
  neon_cyberpunk: [
    'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1511447333015-45b65e60f6d5?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1080&q=85',
  ],
  photorealistic: [
    'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1080&q=85',
    'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1080&q=85',
  ],
};

function generateMockContent(topic, style, count, overlayText) {
  const cleanTopic = topic.trim();
  const styleImages = MOCK_PRESET_IMAGES[style] || MOCK_PRESET_IMAGES.cinematic;

  const captionTemplates = [
    `🚀 ${cleanTopic.toUpperCase()} Hakkında Bilmeniz Gerekenler!\n\nGünümüzün hızla değişen dünyasında ${cleanTopic.toLowerCase()} stratejik bir öneme sahip. Başarı tesadüf değildir; doğru bilgi, vizyon ve disiplinli adımlarla şekillenir.\n\n💡 Siz bu konuda ne düşünüyorsunuz? Yorumlarda buluşalım!\n\n📌 Gönderiyi kaydetmeyi ve ilgilenecek arkadaşlarınla paylaşmayı unutma!`,
    `✨ ${cleanTopic}: Geleceği Şekillendiren Bakış Açısı\n\nAdım adım ilerlemek, büyük hedeflere ulaşmanın en sağlam yoludur. ${cleanTopic.toLowerCase()} alanında fark yaratmak için bugünden harekete geçin.\n\n👇 Deneyimlerinizi bizimle paylaşın!`,
    `🎯 ${cleanTopic} ile Bir Adım Öne Geçin!\n\nHer yeni gün, yeni fırsatlar sunar. Kendinize yatırım yapın ve ${cleanTopic.toLowerCase()} konusundaki gelişmeleri yakından takip edin.`,
  ];

  const selectedCaption = captionTemplates[Math.floor(Math.random() * captionTemplates.length)];

  // Konudan hashtag türet
  const topicWords = cleanTopic.toLowerCase().replace(/[^a-z0-9ğüşıöç ]/gi, '').split(/\s+/).filter(Boolean);
  const baseTags = topicWords.map(w => `#${w}`);
  const extraTags = ['#sosyalmedya', '#dijitalicerik', '#gelisim', '#inovasyon', '#motivasyon', '#vizyon', '#trendler', '#turkiye'];
  const hashtags = Array.from(new Set([...baseTags, ...extraTags])).slice(0, 10);

  const posts = [];
  for (let i = 0; i < count; i++) {
    const imgUrl = styleImages[i % styleImages.length];
    posts.push({
      id: `post-${Date.now()}-${i + 1}`,
      index: i + 1,
      image_url: imgUrl,
      prompt: `${cleanTopic}, ${style} style, ultra detailed, modern aesthetic lighting, 8k resolution`,
      overlay_text: overlayText || cleanTopic,
      caption: selectedCaption,
      hashtags: hashtags,
    });
  }

  return {
    success: true,
    mock: true,
    topic: cleanTopic,
    style,
    count,
    cost_usd: 0.0,
    created_at: new Date().toISOString(),
    posts,
  };
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      topic = '',
      image_count = 1,
      format = 'post_4x5',
      style = 'cinematic',
      quality = 'standard',
      overlay_text = '',
      provider = 'openai',
      mock = false,
    } = body;

    if (!topic || topic.trim().length < 2) {
      return NextResponse.json(
        { error: 'Lütfen en az 2 karakterden oluşan bir konu girin.' },
        { status: 400 }
      );
    }

    const count = Math.min(Math.max(parseInt(image_count, 10) || 1, 1), 4);
    const apiKey = process.env.OPENAI_API_KEY;

    // Eğer mock modu seçildiyse veya API anahtarı yoksa güvenli ve hızlı mock üretim
    if (mock || provider === 'mock' || !apiKey) {
      const mockResult = generateMockContent(topic, style, count, overlay_text);
      return NextResponse.json(mockResult);
    }

    // Gerçek OpenAI Çağrısı (GPT-4o + DALL-E 3)
    try {
      // 1) LLM ile caption, prompt ve hashtag üretimi
      const systemPrompt = `Sen profesyonel bir sosyal medya içerik yöneticisisin. Verilen konuya göre Instagram için yüksek etkileşimli Türkçe bir caption, hashtag'ler ve DALL-E görsel promptları üreteceksin. Yanıtını SADECE geçerli bir JSON formatında ver.
JSON şeması:
{
  "caption": "Instagram gönderi açıklaması...",
  "hashtags": ["#tag1", "#tag2", ...],
  "prompts": ["dalle görsel promptu 1", ...]
}`;

      const llmRes = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: `Konu: ${topic}\nGörsel Sayısı: ${count}\nStil: ${style}\nFormat: ${format}` },
          ],
          response_format: { type: 'json_object' },
        }),
      });

      if (!llmRes.ok) {
        throw new Error(`OpenAI Chat API hatası: ${llmRes.status}`);
      }

      const llmData = await llmRes.json();
      const content = JSON.parse(llmData.choices[0].message.content);

      // 2) DALL-E 3 ile görsel üretimi
      const posts = [];
      const dalleSize = format === 'story_9x16' ? '1024x1792' : format === 'square_1x1' ? '1024x1024' : '1024x1792';

      for (let i = 0; i < count; i++) {
        const imagePrompt = (content.prompts && content.prompts[i]) || `${topic}, ${style} style, visual background, 8k`;
        
        const dalleRes = await fetch('https://api.openai.com/v1/images/generations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model: 'dall-e-3',
            prompt: imagePrompt,
            n: 1,
            size: dalleSize,
            quality: quality === 'hd' ? 'hd' : 'standard',
          }),
        });

        if (!dalleRes.ok) {
          throw new Error(`DALL-E API hatası: ${dalleRes.status}`);
        }

        const dalleData = await dalleRes.json();
        const imageUrl = dalleData.data[0].url;

        posts.push({
          id: `post-${Date.now()}-${i + 1}`,
          index: i + 1,
          image_url: imageUrl,
          prompt: imagePrompt,
          overlay_text: overlay_text || topic,
          caption: content.caption,
          hashtags: content.hashtags || [],
        });
      }

      const costUsd = count * (quality === 'hd' ? 0.08 : 0.04) + 0.005;

      return NextResponse.json({
        success: true,
        mock: false,
        topic,
        style,
        count,
        cost_usd: Number(costUsd.toFixed(4)),
        created_at: new Date().toISOString(),
        posts,
      });
    } catch (apiErr) {
      console.warn('Canlı API hatası, mock moduna dönülüyor:', apiErr);
      // Hata durumunda kullanıcıyı kilitlemeyip fallback mock sun
      const fallback = generateMockContent(topic, style, count, overlay_text);
      fallback.warning = `Canlı API bağlantısı sağlanamadı (${apiErr.message}). Mock önizleme yüklendi.`;
      return NextResponse.json(fallback);
    }
  } catch (err) {
    return NextResponse.json(
      { error: err.message || 'Üretim sırasında bir sunucu hatası oluştu.' },
      { status: 500 }
    );
  }
}
