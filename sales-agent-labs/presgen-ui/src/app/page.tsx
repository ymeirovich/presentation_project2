'use client'

import { useState } from "react"
import { TopBanner } from "@/components/TopBanner"
import { Header } from "@/components/Header"
import { SegmentedTabs } from "@/components/SegmentedTabs"
import { CoreForm } from "@/components/CoreForm"
import { DataForm } from "@/components/DataForm"
import { AssessmentWorkflow } from "@/components/assess/AssessmentWorkflow"
import { VideoWorkflow } from "@/components/video/VideoWorkflow"
import { TrainingWorkflow } from "@/components/training/TrainingWorkflow"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { TabConfig } from "@/lib/types"

const TABS: TabConfig[] = [
  {
    value: "core",
    label: "PresGen Core",
  },
  {
    value: "data",
    label: "PresGen-Data",
  },
  {
    value: "assess",
    label: "PresGen-Assess",
  },
  {
    value: "video",
    label: "PresGen-Video",
    disabled: false,
  },
  {
    value: "training",
    label: "PresGen-Training",
    disabled: false,
  },
]

export default function Home() {
  const [activeTab, setActiveTab] = useState("core")

  const renderTabContent = () => {
    switch (activeTab) {
      case "core":
        return <CoreForm />
      case "data":
        return <DataForm />
      case "assess":
        return <AssessmentWorkflow />
      case "video":
        return <VideoWorkflow />
      case "training":
        return <TrainingWorkflow />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background" suppressHydrationWarning={true}>
      <TopBanner />
      
      <Header>
        <TooltipProvider>
          <div className="flex justify-center w-full">
            <SegmentedTabs
              tabs={TABS.map(tab => ({
                ...tab,
                label: tab.disabled && tab.tooltip ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>{tab.label}</span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{tab.tooltip}</p>
                    </TooltipContent>
                  </Tooltip>
                ) : tab.label
              }))}
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-auto"
            />
          </div>
        </TooltipProvider>
      </Header>

      <main className="container mx-auto px-4 py-8" suppressHydrationWarning={true}>
        <div className="max-w-4xl mx-auto" suppressHydrationWarning={true}>
          {renderTabContent()}
        </div>
      </main>

      <footer className="border-t border-border bg-card/50 mt-16" suppressHydrationWarning={true}>
        <div className="container mx-auto px-4 py-6">
          <div className="text-center text-sm text-muted-foreground">
            <p>PresGen MVP - Transforming content into presentations with AI</p>
            <p className="mt-1">
              Built with Next.js, Tailwind CSS, and powered by Google AI
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
