/**
 * 图片压缩工具
 *
 * 背景：手机拍照原图普遍 6~12MB，且 iPhone 默认输出 HEIC、部分安卓输出 WebP，
 * 而后端 `/ai/recognize-food` 限制「jpg/png 且 ≤5MB」——直接上传必然 400。
 *
 * 本工具在上传前于浏览器端完成：降采样（最长边 ≤1600）→ 转 JPEG → 逐级降质压缩，
 * 既规避大小/格式限制，又显著减少上传耗时与流量；同时把 HEIC/WebP 统一转成 JPEG。
 */

// 动图 / 矢量图不压缩：压缩会丢失动画或产生失真
const SKIP_TYPES = /^image\/(gif|svg\+xml)$/i

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => resolve({ img, url })
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片解码失败'))
    }
    img.src = url
  })
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve) => {
    if (!canvas.toBlob) {
      resolve(null)
      return
    }
    canvas.toBlob((b) => resolve(b), type, quality)
  })
}

/**
 * 压缩图片为 JPEG File。
 * @param {File|Blob} file 原始文件
 * @param {object} [options]
 * @param {number} [options.maxSize=1600]     最长边像素上限
 * @param {number} [options.quality=0.82]     初始 JPEG 质量
 * @param {number} [options.minQuality=0.5]   质量下限
 * @param {number} [options.maxBytes=2097152] 目标体积上限（默认 2MB，后端限 5MB 留足余量）
 * @returns {Promise<File|Blob>} 压缩后的 JPEG，无法压缩时返回原文件
 */
export async function compressImage(file, options = {}) {
  const {
    maxSize = 1600,
    quality = 0.82,
    minQuality = 0.5,
    maxBytes = 2 * 1024 * 1024
  } = options

  if (!file || !(file instanceof Blob)) return file
  if (!file.type || !file.type.startsWith('image/')) return file
  if (SKIP_TYPES.test(file.type)) return file

  let src
  try {
    src = await loadImage(file)
  } catch (e) {
    // 浏览器无法解码该格式（如部分环境不支持 HEIC）→ 原样上传，由后端返回明确错误
    return file
  }

  try {
    const { img, url } = src
    const w0 = img.naturalWidth || img.width
    const h0 = img.naturalHeight || img.height
    if (!w0 || !h0) return file

    const scale = Math.min(1, maxSize / Math.max(w0, h0))
    const w = Math.max(1, Math.round(w0 * scale))
    const h = Math.max(1, Math.round(h0 * scale))

    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    // 铺白底：JPEG 不支持透明通道，PNG 透明区域否则会变黑
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(img, 0, 0, w, h)

    let q = quality
    let blob = await canvasToBlob(canvas, 'image/jpeg', q)
    // 仍超目标体积则逐级降质重试
    while (blob && blob.size > maxBytes && q > minQuality) {
      q = Math.max(minQuality, q - 0.1)
      blob = await canvasToBlob(canvas, 'image/jpeg', q)
    }
    if (!blob) return file

    // 原图本就是 jpg/png 且压缩后反而更大（如极小图）→ 保留原图
    if (blob.size >= file.size && /^image\/(jpeg|png)$/i.test(file.type)) return file

    const base = (file.name || 'photo').replace(/\.[^.]+$/, '')
    return new File([blob], `${base}.jpg`, {
      type: 'image/jpeg',
      lastModified: Date.now()
    })
  } finally {
    if (src && src.url) URL.revokeObjectURL(src.url)
  }
}

export default compressImage
