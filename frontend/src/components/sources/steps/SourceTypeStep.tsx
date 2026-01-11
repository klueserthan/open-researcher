"use client"

import React, { useMemo, useState } from "react"
import { Control, FieldErrors, UseFormRegister, useWatch } from "react-hook-form"
import { FileIcon, LinkIcon, FileTextIcon, BookOpenIcon, SearchIcon, LoaderIcon } from "lucide-react"
import { FormSection } from "@/components/ui/form-section"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Controller } from "react-hook-form"
import { sourcesApi } from "@/lib/api/sources"
import type { ZoteroItemResponse } from "@/lib/types/api"
import { toast } from "sonner"

interface CreateSourceFormData {
  type: 'link' | 'upload' | 'text' | 'zotero'
  title?: string
  url?: string
  content?: string
  file?: FileList | File
  notebooks?: string[]
  transformations?: string[]
  embed: boolean
  async_processing: boolean
  zotero_item_key?: string
}

// Helper functions for batch URL parsing
function parseUrls(text: string): string[] {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
}

function validateUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

export function parseAndValidateUrls(text: string): {
  valid: string[]
  invalid: { url: string; line: number }[]
} {
  const lines = text.split('\n')
  const valid: string[] = []
  const invalid: { url: string; line: number }[] = []

  lines.forEach((line, index) => {
    const trimmed = line.trim()
    if (trimmed.length === 0) return // skip empty lines

    if (validateUrl(trimmed)) {
      valid.push(trimmed)
    } else {
      invalid.push({ url: trimmed, line: index + 1 })
    }
  })

  return { valid, invalid }
}

const SOURCE_TYPES = [
  {
    value: 'link' as const,
    label: 'Link',
    icon: LinkIcon,
    description: 'Add a web page or URL',
  },
  {
    value: 'upload' as const,
    label: 'Upload',
    icon: FileIcon,
    description: 'Upload a document or file',
  },
  {
    value: 'text' as const,
    label: 'Text',
    icon: FileTextIcon,
    description: 'Add text content directly',
  },
  {
    value: 'zotero' as const,
    label: 'Zotero',
    icon: BookOpenIcon,
    description: 'Import from Zotero library',
  },
]

interface SourceTypeStepProps {
  control: Control<CreateSourceFormData>
  register: UseFormRegister<CreateSourceFormData>
  errors: FieldErrors<CreateSourceFormData>
  urlValidationErrors?: { url: string; line: number }[]
  onClearUrlErrors?: () => void
  setValue?: (name: keyof CreateSourceFormData, value: any) => void
}

const MAX_BATCH_SIZE = 50

export function SourceTypeStep({ control, register, errors, urlValidationErrors, onClearUrlErrors, setValue }: SourceTypeStepProps) {
  // Watch the selected type and inputs to detect batch mode
  const selectedType = useWatch({ control, name: 'type' })
  const urlInput = useWatch({ control, name: 'url' })
  const fileInput = useWatch({ control, name: 'file' })

  // Zotero search state
  const [zoteroSearchQuery, setZoteroSearchQuery] = useState('')
  const [zoteroSearching, setZoteroSearching] = useState(false)
  const [zoteroResults, setZoteroResults] = useState<ZoteroItemResponse[]>([])
  const [selectedZoteroItem, setSelectedZoteroItem] = useState<ZoteroItemResponse | null>(null)

  // Batch mode detection
  const { isBatchMode, itemCount, urlCount, fileCount } = useMemo(() => {
    let urlCount = 0
    let fileCount = 0

    if (selectedType === 'link' && urlInput) {
      const urls = parseUrls(urlInput)
      urlCount = urls.length
    }

    if (selectedType === 'upload' && fileInput) {
      const fileList = fileInput as FileList
      fileCount = fileList?.length || 0
    }

    const isBatchMode = urlCount > 1 || fileCount > 1
    const itemCount = selectedType === 'link' ? urlCount : fileCount

    return { isBatchMode, itemCount, urlCount, fileCount }
  }, [selectedType, urlInput, fileInput])

  // Zotero search handler
  const handleZoteroSearch = async () => {
    if (!zoteroSearchQuery.trim()) {
      toast.error('Please enter a search query')
      return
    }

    setZoteroSearching(true)
    try {
      const results = await sourcesApi.searchZotero({
        query: zoteroSearchQuery,
        limit: 20
      })
      setZoteroResults(results)
      
      if (results.length === 0) {
        toast.info('No results found')
      }
    } catch (error: unknown) {
      console.error('Zotero search failed:', error)
      toast.error('Zotero search failed. Please try again later.')
    } finally {
      setZoteroSearching(false)
    }
  }

  // Check for batch size limit
  const isOverLimit = itemCount > MAX_BATCH_SIZE
  return (
    <div className="space-y-6">
      <FormSection
        title="Source Type"
        description="Choose how you want to add your content"
      >
        <Controller
          control={control}
          name="type"
          render={({ field }) => (
            <Tabs 
              value={field.value || ''} 
              onValueChange={(value) => {
                field.onChange(value as 'link' | 'upload' | 'text' | 'zotero')
                // Handle state cleanup when switching source types
                if (value !== 'zotero') {
                  // Clear Zotero-specific state and form field
                  setZoteroResults([])
                  setSelectedZoteroItem(null)
                  if (setValue) {
                    setValue('zotero_item_key', '')
                  }
                } else {
                  // Clear other source type fields when switching to Zotero
                  if (setValue) {
                    setValue('url', '')
                    setValue('content', '')
                    setValue('file', undefined as unknown as FileList | File)
                  }
                  // Reset Zotero search query for clean state
                  setZoteroSearchQuery('')
                }
              }}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-4">
                {SOURCE_TYPES.map((type) => {
                  const Icon = type.icon
                  return (
                    <TabsTrigger key={type.value} value={type.value} className="gap-2">
                      <Icon className="h-4 w-4" />
                      {type.label}
                    </TabsTrigger>
                  )
                })}
              </TabsList>
              
              {SOURCE_TYPES.map((type) => (
                <TabsContent key={type.value} value={type.value} className="mt-4">
                  <p className="text-sm text-muted-foreground mb-4">{type.description}</p>
                  
                  {/* Type-specific fields */}
                  {type.value === 'link' && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label htmlFor="url">URL(s) *</Label>
                        {urlCount > 0 && (
                          <Badge variant={isOverLimit ? "destructive" : "secondary"}>
                            {urlCount} URL{urlCount !== 1 ? 's' : ''}
                            {isOverLimit && ` (max ${MAX_BATCH_SIZE})`}
                          </Badge>
                        )}
                      </div>
                      <Textarea
                        id="url"
                        {...register('url', {
                          onChange: () => onClearUrlErrors?.()
                        })}
                        placeholder="Enter URLs, one per line&#10;https://example.com/article1&#10;https://example.com/article2"
                        rows={urlCount > 1 ? 6 : 2}
                        className="font-mono text-sm"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Paste multiple URLs (one per line) to batch import
                      </p>
                      {errors.url && (
                        <p className="text-sm text-destructive mt-1">{errors.url.message}</p>
                      )}
                      {urlValidationErrors && urlValidationErrors.length > 0 && (
                        <div className="mt-2 p-3 bg-destructive/10 rounded-md border border-destructive/20">
                          <p className="text-sm font-medium text-destructive mb-2">
                            Invalid URLs detected:
                          </p>
                          <ul className="space-y-1">
                            {urlValidationErrors.map((error, idx) => (
                              <li key={idx} className="text-xs text-destructive flex items-start gap-2">
                                <span className="font-mono bg-destructive/20 px-1 rounded">
                                  Line {error.line}
                                </span>
                                <span className="truncate">{error.url}</span>
                              </li>
                            ))}
                          </ul>
                          <p className="text-xs text-muted-foreground mt-2">
                            Please fix or remove invalid URLs to continue
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'upload' && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label htmlFor="file">File(s) *</Label>
                        {fileCount > 0 && (
                          <Badge variant={isOverLimit ? "destructive" : "secondary"}>
                            {fileCount} file{fileCount !== 1 ? 's' : ''}
                            {isOverLimit && ` (max ${MAX_BATCH_SIZE})`}
                          </Badge>
                        )}
                      </div>
                      <Input
                        id="file"
                        type="file"
                        multiple
                        {...register('file')}
                        accept=".pdf,.doc,.docx,.pptx,.ppt,.xlsx,.xls,.txt,.md,.epub,.mp4,.avi,.mov,.wmv,.mp3,.wav,.m4a,.aac,.jpg,.jpeg,.png,.tiff,.zip,.tar,.gz,.html"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Select multiple files to batch import. Supported: Documents (PDF, DOC, DOCX, PPT, XLS, EPUB, TXT, MD), Media (MP4, MP3, WAV, M4A), Images (JPG, PNG), Archives (ZIP)
                      </p>
                      {fileCount > 1 && fileInput instanceof FileList && (
                        <div className="mt-2 p-3 bg-muted rounded-md">
                          <p className="text-xs font-medium mb-2">Selected files:</p>
                          <ul className="space-y-1 max-h-32 overflow-y-auto">
                            {Array.from(fileInput).map((file, idx) => (
                              <li key={idx} className="text-xs text-muted-foreground flex items-center gap-2">
                                <FileIcon className="h-3 w-3" />
                                <span className="truncate">{file.name}</span>
                                <span className="text-muted-foreground/50">
                                  ({(file.size / 1024).toFixed(1)} KB)
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {errors.file && (
                        <p className="text-sm text-destructive mt-1">{errors.file.message}</p>
                      )}
                      {isOverLimit && selectedType === 'upload' && (
                        <p className="text-sm text-destructive mt-1">
                          Maximum {MAX_BATCH_SIZE} files allowed per batch
                        </p>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'text' && (
                    <div>
                      <Label htmlFor="content" className="mb-2 block">Text Content *</Label>
                      <Textarea
                        id="content"
                        {...register('content')}
                        placeholder="Paste or type your content here..."
                        rows={6}
                      />
                      {errors.content && (
                        <p className="text-sm text-destructive mt-1">{errors.content.message}</p>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'zotero' && (
                    <div className="space-y-4">
                      {/* Zotero Search */}
                      <div>
                        <Label htmlFor="zotero_search">Search Zotero Library</Label>
                        <div className="flex gap-2 mt-2">
                          <Input
                            id="zotero_search"
                            value={zoteroSearchQuery}
                            onChange={(e) => setZoteroSearchQuery(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault()
                                handleZoteroSearch()
                              }
                            }}
                            placeholder="Search by title, author, or metadata..."
                            disabled={zoteroSearching}
                          />
                          <Button 
                            type="button" 
                            onClick={handleZoteroSearch}
                            disabled={zoteroSearching || !zoteroSearchQuery.trim()}
                          >
                            {zoteroSearching ? (
                              <LoaderIcon className="h-4 w-4 animate-spin" />
                            ) : (
                              <SearchIcon className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Search your Zotero library by title, author, or other metadata
                        </p>
                      </div>

                      {/* Search Results */}
                      {zoteroResults.length > 0 && (
                        <div className="border rounded-lg overflow-hidden">
                          <div className="bg-muted px-3 py-2 border-b">
                            <p className="text-sm font-medium">{zoteroResults.length} result{zoteroResults.length !== 1 ? 's' : ''} found</p>
                          </div>
                          <div className="max-h-96 overflow-y-auto">
                            {zoteroResults.map((item) => (
                              <div
                                key={item.key}
                                className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-muted/50 transition-colors ${
                                  selectedZoteroItem?.key === item.key ? 'bg-primary/10' : ''
                                }`}
                                onClick={() => {
                                  setSelectedZoteroItem(item)
                                  // Update form field using setValue from react-hook-form
                                  if (setValue) {
                                    setValue('zotero_item_key', item.key)
                                  }
                                }}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1 min-w-0">
                                    <h4 className="text-sm font-medium truncate">{item.title}</h4>
                                    {item.authors.length > 0 && (
                                      <p className="text-xs text-muted-foreground mt-1">
                                        {item.authors.join(', ')}
                                      </p>
                                    )}
                                    {item.year && (
                                      <p className="text-xs text-muted-foreground">{item.year}</p>
                                    )}
                                    {item.abstract && (
                                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                        {item.abstract}
                                      </p>
                                    )}
                                  </div>
                                  {selectedZoteroItem?.key === item.key && (
                                    <Badge variant="default" className="shrink-0">Selected</Badge>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Hidden field for form submission */}
                      <input
                        type="hidden"
                        {...register('zotero_item_key')}
                      />
                      
                      {errors.zotero_item_key && (
                        <p className="text-sm text-destructive">{errors.zotero_item_key.message}</p>
                      )}
                    </div>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          )}
        />
        {errors.type && (
          <p className="text-sm text-destructive mt-1">{errors.type.message}</p>
        )}
      </FormSection>

      {/* Hide title field in batch mode - titles will be auto-generated */}
      {!isBatchMode && selectedType !== 'zotero' && (
        <FormSection
          title={selectedType === 'text' ? "Title *" : "Title (optional)"}
          description={selectedType === 'text'
            ? "A title is required for text content"
            : "If left empty, a title will be generated from the content"
          }
        >
          <Input
            id="title"
            {...register('title')}
            placeholder="Give your source a descriptive title"
          />
          {errors.title && (
            <p className="text-sm text-destructive mt-1">{errors.title.message}</p>
          )}
        </FormSection>
      )}

      {/* Selected Zotero item info */}
      {selectedType === 'zotero' && selectedZoteroItem && (
        <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="flex items-start gap-3">
            <BookOpenIcon className="h-5 w-5 text-primary mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">Selected: {selectedZoteroItem.title}</p>
              {selectedZoteroItem.authors.length > 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  {selectedZoteroItem.authors.join(', ')}
                </p>
              )}
              {selectedZoteroItem.year && (
                <p className="text-xs text-muted-foreground">{selectedZoteroItem.year}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Batch mode indicator */}
      {isBatchMode && (
        <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="default">Batch Mode</Badge>
            <span className="text-sm font-medium">
              {itemCount} {selectedType === 'link' ? 'URLs' : 'files'} will be processed
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Titles will be automatically generated for each source.
            The same notebooks and transformations will be applied to all items.
          </p>
        </div>
      )}
    </div>
  )
}
