// Server-side file utilities for processing uploaded files

// Helper function to read file content based on file type
export async function readFileContent(file: File): Promise<string> {
  const fileType = file.type.toLowerCase()
  const fileName = file.name.toLowerCase()

  // Handle text files first (most reliable)
  if (fileType === 'text/plain' || fileName.endsWith('.txt')) {
    return readTextContent(file)
  }
  
  // For PDF files, provide helpful error message
  if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
    throw new Error('PDF files are not currently supported due to a PDF.js worker configuration issue. Please convert your PDF content to a .txt file, save as DOCX, or copy-paste the text directly into the Report Text field.')
  }
  
  if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || fileName.endsWith('.docx')) {
    throw new Error('DOCX files are not currently supported for server-side processing. Please save your document as a .txt file or copy-paste the text directly into the Report Text field.')
  }
  
  // Default to text processing for unknown types
  return readTextContent(file)
}

// Read text files
async function readTextContent(file: File): Promise<string> {
  try {
    const buffer = await file.arrayBuffer()
    const text = new TextDecoder('utf-8').decode(buffer)
    const trimmedText = text.trim()
    
    if (!trimmedText) {
      throw new Error('Text file appears to be empty')
    }
    
    return trimmedText
  } catch (error) {
    if (error instanceof Error && error.message.includes('empty')) {
      throw error
    }
    throw new Error('Failed to read text file. Please ensure the file is a valid UTF-8 encoded text file.')
  }
}