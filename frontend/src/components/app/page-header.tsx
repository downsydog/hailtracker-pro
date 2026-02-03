import * as React from "react"

interface PageHeaderAction {
  label: string
  onClick: () => void
  icon?: React.ComponentType<{ className?: string }>
  variant?: 'default' | 'outline' | 'ghost'
}

interface PageHeaderProps {
  title: string
  description?: string
  children?: React.ReactNode
  actions?: PageHeaderAction[]
}

export function PageHeader({ title, description, children, actions }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        {actions?.map((action, idx) => (
          <button
            key={idx}
            onClick={action.onClick}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
          >
            {action.icon && <action.icon className="h-4 w-4" />}
            {action.label}
          </button>
        ))}
        {children}
      </div>
    </div>
  )
}
