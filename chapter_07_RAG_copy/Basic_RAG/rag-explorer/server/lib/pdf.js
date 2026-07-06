import fs from 'node:fs'
import path from 'node:path'
// Import the inner module directly — pdf-parse's index.js runs a debug harness
// on import that looks for a test file and throws. The lib entry is clean.
import pdfParse from 'pdf-parse/lib/pdf-parse.js'

// Lists every *.pdf in the data directory.
export function listPdfs(dataDir) {
  if (!fs.existsSync(dataDir)) return []
  return fs
    .readdirSync(dataDir)
    .filter((f) => f.toLowerCase().endsWith('.pdf'))
    .map((f) => ({ file: f, path: path.join(dataDir, f) }))
}

// Extracts raw text + page count from one PDF.
export async function extractPdf(filePath) {
  const buf = fs.readFileSync(filePath)
  const data = await pdfParse(buf)
  return {
    text: data.text || '',
    numPages: data.numpages || 0,
    info: data.info || {},
  }
}
