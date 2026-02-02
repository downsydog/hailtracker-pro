import * as React from "react"
import { usePortal } from "@/contexts/portal-context"
import { portalApi, PortalNotificationPrefs } from "@/api/portal"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  User,
  Bell,
  Lock,
  Mail,
  Phone,
  MessageSquare,
  Car,
  CheckCircle,
  Calendar,
  Save,
} from "lucide-react"

export function PortalSettingsPage() {
  const { customer, refreshCustomer } = usePortal()
  const [profile, setProfile] = React.useState({
    first_name: customer?.first_name || "",
    last_name: customer?.last_name || "",
    email: customer?.email || "",
    phone: customer?.phone || "",
  })
  const [notifications, setNotifications] = React.useState<PortalNotificationPrefs>({
    email_enabled: true,
    sms_enabled: true,
    push_enabled: false,
    notify_on_status_change: true,
    notify_on_message: true,
    notify_on_appointment: true,
    notify_on_completion: true,
  })
  const [saving, setSaving] = React.useState(false)
  const [passwordDialogOpen, setPasswordDialogOpen] = React.useState(false)
  const [passwordData, setPasswordData] = React.useState({
    current: "",
    new: "",
    confirm: "",
  })

  React.useEffect(() => {
    const fetchPrefs = async () => {
      try {
        const prefs = await portalApi.getNotificationPrefs()
        setNotifications(prefs)
      } catch {
        // Use defaults
      }
    }
    fetchPrefs()
  }, [])

  React.useEffect(() => {
    if (customer) {
      setProfile({
        first_name: customer.first_name,
        last_name: customer.last_name,
        email: customer.email,
        phone: customer.phone || "",
      })
    }
  }, [customer])

  const handleSaveProfile = async () => {
    setSaving(true)
    try {
      await portalApi.updateProfile(profile)
      await refreshCustomer()
    } catch (error) {
      console.error("Failed to update profile:", error)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveNotifications = async () => {
    setSaving(true)
    try {
      await portalApi.updateNotificationPrefs(notifications)
    } catch (error) {
      console.error("Failed to update notifications:", error)
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async () => {
    if (passwordData.new !== passwordData.confirm) {
      return
    }
    try {
      await portalApi.changeAccessCode(passwordData.current, passwordData.new)
      setPasswordDialogOpen(false)
      setPasswordData({ current: "", new: "", confirm: "" })
    } catch (error) {
      console.error("Failed to change access code:", error)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your profile and notification preferences
        </p>
      </div>

      {/* Profile Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile Information
          </CardTitle>
          <CardDescription>
            Update your personal information
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First Name</Label>
              <Input
                id="first_name"
                value={profile.first_name}
                onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last Name</Label>
              <Input
                id="last_name"
                value={profile.last_name}
                onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">
              <Mail className="h-4 w-4 inline mr-2" />
              Email Address
            </Label>
            <Input
              id="email"
              type="email"
              value={profile.email}
              onChange={(e) => setProfile({ ...profile, email: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">
              <Phone className="h-4 w-4 inline mr-2" />
              Phone Number
            </Label>
            <Input
              id="phone"
              type="tel"
              value={profile.phone}
              onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            />
          </div>
          <Button onClick={handleSaveProfile} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            Save Profile
          </Button>
        </CardContent>
      </Card>

      {/* Notification Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notification Preferences
          </CardTitle>
          <CardDescription>
            Choose how and when you want to be notified
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Notification Channels */}
          <div>
            <h4 className="font-medium mb-4">Notification Channels</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-muted-foreground">
                      Receive updates via email
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.email_enabled}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, email_enabled: checked })
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Phone className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">SMS Notifications</p>
                    <p className="text-sm text-muted-foreground">
                      Receive text message updates
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.sms_enabled}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, sms_enabled: checked })
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bell className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Push Notifications</p>
                    <p className="text-sm text-muted-foreground">
                      Browser push notifications
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.push_enabled}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, push_enabled: checked })
                  }
                />
              </div>
            </div>
          </div>

          {/* Notification Types */}
          <div>
            <h4 className="font-medium mb-4">Notify Me When</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Car className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Job Status Changes</p>
                    <p className="text-sm text-muted-foreground">
                      When your repair status updates
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.notify_on_status_change}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, notify_on_status_change: checked })
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MessageSquare className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">New Messages</p>
                    <p className="text-sm text-muted-foreground">
                      When you receive a new message
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.notify_on_message}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, notify_on_message: checked })
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Appointment Reminders</p>
                    <p className="text-sm text-muted-foreground">
                      Reminders for upcoming appointments
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.notify_on_appointment}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, notify_on_appointment: checked })
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Job Completion</p>
                    <p className="text-sm text-muted-foreground">
                      When your vehicle is ready for pickup
                    </p>
                  </div>
                </div>
                <Switch
                  checked={notifications.notify_on_completion}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, notify_on_completion: checked })
                  }
                />
              </div>
            </div>
          </div>

          <Button onClick={handleSaveNotifications} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            Save Preferences
          </Button>
        </CardContent>
      </Card>

      {/* Security */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Security
          </CardTitle>
          <CardDescription>
            Manage your access code and security settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={() => setPasswordDialogOpen(true)}>
            <Lock className="h-4 w-4 mr-2" />
            Change Access Code
          </Button>
        </CardContent>
      </Card>

      {/* Change Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Access Code</DialogTitle>
            <DialogDescription>
              Enter your current access code and choose a new one
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current">Current Access Code</Label>
              <Input
                id="current"
                type="password"
                value={passwordData.current}
                onChange={(e) =>
                  setPasswordData({ ...passwordData, current: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new">New Access Code</Label>
              <Input
                id="new"
                type="password"
                value={passwordData.new}
                onChange={(e) =>
                  setPasswordData({ ...passwordData, new: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Confirm New Access Code</Label>
              <Input
                id="confirm"
                type="password"
                value={passwordData.confirm}
                onChange={(e) =>
                  setPasswordData({ ...passwordData, confirm: e.target.value })
                }
              />
              {passwordData.new &&
                passwordData.confirm &&
                passwordData.new !== passwordData.confirm && (
                  <p className="text-sm text-red-600">Access codes don't match</p>
                )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleChangePassword}
              disabled={
                !passwordData.current ||
                !passwordData.new ||
                passwordData.new !== passwordData.confirm
              }
            >
              Update Access Code
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
