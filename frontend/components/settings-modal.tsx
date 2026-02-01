"use client"

import { ReactNode } from 'react'
import { X, Settings as SettingsIcon, Volume2, Sparkles, Eye, MessageSquare } from 'lucide-react'
import { useSettings } from '@/contexts/settings-context'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { settings, updateSettings, resetSettings } = useSettings()

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative glass-overlay lavender-glow rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <SettingsIcon className="size-6 text-lavender-400" />
            <h2 className="text-2xl font-bold text-white">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="size-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors"
            aria-label="Close settings"
          >
            <X className="size-5 text-white/60" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-140px)] custom-scrollbar">
          {/* Playback Settings */}
          <SettingsSection
            icon={<Volume2 className="size-5" />}
            title="Playback"
            description="Control video playback behavior"
          >
            <ToggleSetting
              label="Auto-pause on voice input"
              description="Automatically pause video when you start speaking"
              checked={settings.autoPauseOnVoice}
              onChange={(checked) => updateSettings({ autoPauseOnVoice: checked })}
            />

            <SliderSetting
              label="Volume ducking during AI speech"
              description="How much to lower video volume (percentage)"
              value={settings.volumeDuckingPercent}
              onChange={(value) => updateSettings({ volumeDuckingPercent: value })}
              min={0}
              max={50}
              step={5}
              suffix="%"
            />

            <ToggleSetting
              label="Show timer during playback"
              description="Display time counter while video is playing"
              checked={settings.showTimerDuringPlayback}
              onChange={(checked) => updateSettings({ showTimerDuringPlayback: checked })}
            />
          </SettingsSection>

          {/* AI Settings */}
          <SettingsSection
            icon={<Sparkles className="size-5" />}
            title="AI Assistant"
            description="Configure AI behavior"
          >
            <ToggleSetting
              label="Voice responses"
              description="Enable text-to-speech for AI answers"
              checked={settings.voiceResponseEnabled}
              onChange={(checked) => updateSettings({ voiceResponseEnabled: checked })}
            />

            <ToggleSetting
              label="Auto-submit voice transcripts"
              description="Automatically send questions after voice recognition"
              checked={settings.autoSubmitVoice}
              onChange={(checked) => updateSettings({ autoSubmitVoice: checked })}
            />

            <SelectSetting
              label="Response verbosity"
              description="Choose answer detail level"
              value={settings.responseVerbosity}
              onChange={(value) => updateSettings({ responseVerbosity: value as 'concise' | 'detailed' })}
              options={[
                { value: 'concise', label: 'Concise' },
                { value: 'detailed', label: 'Detailed' }
              ]}
            />
          </SettingsSection>

          {/* Accessibility Settings */}
          <SettingsSection
            icon={<Eye className="size-5" />}
            title="Accessibility"
            description="Visual and interaction preferences"
          >
            <ToggleSetting
              label="High contrast mode"
              description="Increase contrast for better visibility"
              checked={settings.highContrast}
              onChange={(checked) => updateSettings({ highContrast: checked })}
            />

            <ToggleSetting
              label="Reduced motion"
              description="Minimize animations and transitions"
              checked={settings.reducedMotion}
              onChange={(checked) => updateSettings({ reducedMotion: checked })}
            />
          </SettingsSection>

          {/* Commentary Settings */}
          <SettingsSection
            icon={<MessageSquare className="size-5" />}
            title="Commentary"
            description="Customize the AI commentary feed"
          >
            <ToggleSetting
              label="Auto-scroll to new items"
              description="Automatically scroll when new commentary appears"
              checked={settings.commentaryAutoScroll}
              onChange={(checked) => updateSettings({ commentaryAutoScroll: checked })}
            />

            <SliderSetting
              label="Maximum items in feed"
              description="Number of commentary items to keep visible"
              value={settings.maxCommentaryItems}
              onChange={(value) => updateSettings({ maxCommentaryItems: value })}
              min={5}
              max={50}
              step={5}
            />

            <ToggleSetting
              label="Show timestamps"
              description="Display time for each commentary item"
              checked={settings.showTimestamps}
              onChange={(checked) => updateSettings({ showTimestamps: checked })}
            />
          </SettingsSection>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-white/10">
          <button
            onClick={resetSettings}
            className="px-4 py-2 text-sm text-white/60 hover:text-white transition-colors"
          >
            Reset to Defaults
          </button>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-lavender-500 hover:bg-lavender-600 text-white rounded-lg font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}

// Helper Components

interface SettingsSectionProps {
  icon: ReactNode
  title: string
  description: string
  children: ReactNode
}

function SettingsSection({ icon, title, description, children }: SettingsSectionProps) {
  return (
    <div className="mb-8 last:mb-0">
      <div className="flex items-center gap-2 mb-3">
        <div className="text-lavender-400">{icon}</div>
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      <p className="text-sm text-white/60 mb-4">{description}</p>
      <div className="space-y-4">
        {children}
      </div>
    </div>
  )
}

interface ToggleSettingProps {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

function ToggleSetting({ label, description, checked, onChange }: ToggleSettingProps) {
  return (
    <div className="flex items-start justify-between gap-4 p-3 rounded-lg hover:bg-white/5 transition-colors">
      <div className="flex-1">
        <div className="text-sm font-medium text-white mb-1">{label}</div>
        <div className="text-xs text-white/50">{description}</div>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-lavender-500' : 'bg-white/20'
        }`}
        role="switch"
        aria-checked={checked}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}

interface SliderSettingProps {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step: number
  suffix?: string
}

function SliderSetting({ label, description, value, onChange, min, max, step, suffix = '' }: SliderSettingProps) {
  return (
    <div className="p-3 rounded-lg hover:bg-white/5 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium text-white">{label}</div>
        <div className="text-sm font-mono text-lavender-400">{value}{suffix}</div>
      </div>
      <div className="text-xs text-white/50 mb-3">{description}</div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-lavender-500 [&::-webkit-slider-thumb]:cursor-pointer [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-lavender-500 [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer"
      />
    </div>
  )
}

interface SelectSettingProps {
  label: string
  description: string
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
}

function SelectSetting({ label, description, value, onChange, options }: SelectSettingProps) {
  return (
    <div className="p-3 rounded-lg hover:bg-white/5 transition-colors">
      <div className="text-sm font-medium text-white mb-1">{label}</div>
      <div className="text-xs text-white/50 mb-3">{description}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:border-lavender-500 transition-colors"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value} className="bg-slate-900">
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
