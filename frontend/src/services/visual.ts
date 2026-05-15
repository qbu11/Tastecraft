import { api } from './api'

/* ── Types ── */

export interface CardStyle {
  background_color: string
  accent_color: string
  text_color: string
  font_name: string
  title_size: number
  body_size: number
  card_width: number
  card_height: number
  padding: number
}

export interface SlideInfo {
  index: number
  image_url: string
  text_content: string
}

export interface CarouselResponse {
  slides: SlideInfo[]
  total_slides: number
  style_used: CardStyle
}

export interface StylePreset {
  name: string
  label: string
  description: string
  style: CardStyle
}

export interface StyleListResponse {
  styles: StylePreset[]
}

export interface PreviewSlideResponse {
  image_base64: string
  format: string
}

/* ── API functions ── */

/**
 * Generate a full carousel from a content record.
 */
export async function generateCarousel(params: {
  content_id: number
  num_slides?: number
  style?: Partial<CardStyle>
}) {
  const { data } = await api.post<CarouselResponse>(
    '/v1/visual/generate-carousel',
    params,
  )
  return data
}

/**
 * Preview a single slide (returns base64 image).
 */
export async function previewSlide(params: {
  text: string
  subtitle?: string
  slide_type?: 'cover' | 'content' | 'cta'
  style?: Partial<CardStyle>
}) {
  const { data } = await api.post<PreviewSlideResponse>(
    '/v1/visual/preview-slide',
    params,
  )
  return data
}

/**
 * List available preset card styles.
 */
export async function getStyles() {
  const { data } = await api.get<StyleListResponse>('/v1/visual/styles')
  return data
}

/**
 * Upload a user image for use in cards.
 */
export async function uploadImage(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<{
    filename: string
    url: string
    size_bytes: number
  }>('/v1/visual/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/**
 * Download all carousel slides as a ZIP blob.
 * (Client-side ZIP generation — uses the image URLs from the carousel response.)
 */
export async function downloadCarouselAsZip(slides: SlideInfo[]): Promise<Blob> {
  // Fetch all images
  const blobs = await Promise.all(
    slides.map(async (slide) => {
      const resp = await fetch(slide.image_url)
      return resp.blob()
    }),
  )

  // Simple approach: return individual blobs concatenated into a tar-like format
  // For MVP, we just trigger individual downloads. ZIP requires a library (e.g. jszip).
  // This is a placeholder that returns the first image blob.
  // TODO: integrate jszip for proper ZIP download
  return blobs[0]
}
