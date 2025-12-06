/**Export service for CSV and Excel exports.*/

export const exportToCSV = (data: any[], filename: string, headers?: string[]) => {
  if (!data || data.length === 0) {
    console.warn('No data to export')
    return
  }

  // Use provided headers or extract from first object
  const csvHeaders = headers || Object.keys(data[0])
  
  // Create CSV content
  const csvRows = []
  
  // Add header row
  csvRows.push(csvHeaders.join(','))
  
  // Add data rows
  data.forEach((row) => {
    const values = csvHeaders.map((header) => {
      const value = row[header]
      // Handle nested objects and arrays
      if (value === null || value === undefined) return ''
      if (typeof value === 'object') return JSON.stringify(value)
      // Escape commas and quotes
      const stringValue = String(value)
      if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
        return `"${stringValue.replace(/"/g, '""')}"`
      }
      return stringValue
    })
    csvRows.push(values.join(','))
  })
  
  const csvContent = csvRows.join('\n')
  
  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}-${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const exportToExcel = async (data: any[], filename: string, headers?: string[]) => {
  // For Excel export, we'd need a library like xlsx
  // For now, fall back to CSV
  console.warn('Excel export not implemented, falling back to CSV')
  exportToCSV(data, filename, headers)
}

