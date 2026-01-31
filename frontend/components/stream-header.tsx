"use client"

import { Snowflake } from "lucide-react"

export function StreamHeader() {
  return (
    <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-6 lg:px-12 py-4 lg:py-6 nav-gradient z-50">
      <div className="flex items-center gap-3 lg:gap-4">
        <div className="size-8 lg:size-10 text-lavender-300 flex items-center justify-center">
          <Snowflake className="size-6 lg:size-8" />
        </div>
        <h2 className="text-white text-lg lg:text-2xl font-light tracking-tight">
          WinterStream <span className="font-bold text-lavender-400">AI</span>
        </h2>
      </div>
      
      <div className="flex flex-1 justify-end gap-6 lg:gap-10 items-center">
        <nav className="hidden xl:flex items-center gap-10">
          <a className="text-white/70 hover:text-white text-sm font-medium transition-colors" href="#">
            Live Events
          </a>
          <a className="text-white/70 hover:text-white text-sm font-medium transition-colors" href="#">
            Athlete Insights
          </a>
          <a className="text-white/70 hover:text-white text-sm font-medium transition-colors" href="#">
            Medal Tally
          </a>
        </nav>
        
        <div className="hidden lg:block h-6 w-px bg-white/20" />
        
        <div className="flex items-center gap-4 lg:gap-6">
          <button className="bg-lavender-500/80 backdrop-blur-md text-white px-4 lg:px-6 py-2 rounded-full text-xs lg:text-sm font-bold hover:bg-lavender-500 transition-all border border-white/20">
            Premium
          </button>
          <div 
            className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-8 lg:size-10 border-2 border-white/40"
            style={{
              backgroundImage: `url("https://lh3.googleusercontent.com/aida-public/AB6AXuBY2O1WuPQIaHklwChZK5_XzbAVczkUGiPy1SUM5z1LodL2gwBOcdsR0_ERVm8a08WVKmNJggaEgSayU-EhsBSORRU9VrdLzy4gb9ctwdhttFfwL4vt8Qotp37f4CpseU1Tn91lvxZm6lD_bKTVTZctyZrWw1VAfksC5-agIIGZrsYUJT53gnjOm3MeRgpCcpG7Vi5OR8eWvWSASZFHSolDxOyQkwtbZgIhistGScxKdVzVPWDjb5thrEH0XxvL8tSaZzZlpskZTg")`
            }}
            aria-label="User profile"
          />
        </div>
      </div>
    </header>
  )
}
