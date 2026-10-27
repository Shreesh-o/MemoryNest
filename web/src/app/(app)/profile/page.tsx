"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  authMe,
  authUpdateProfile,
  authChangePassword,
  authDeactivateAccount,
  type UserPublic,
} from "@/lib/api"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  UserIcon,
  MailIcon,
  KeyRoundIcon,
  ShieldAlertIcon,
  Loader2Icon,
  CheckCircle2Icon,
  AlertTriangleIcon,
} from "lucide-react"

export default function ProfilePage() {
  const router = useRouter()
  const queryClient = useQueryClient()

  const { data: user, isLoading: isUserLoading } = useQuery<UserPublic>({
    queryKey: ["me"],
    queryFn: authMe,
  })

  // Profile Form state
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [isSavingProfile, setIsSavingProfile] = useState(false)

  // Password Form state
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isChangingPassword, setIsChangingPassword] = useState(false)

  // Deactivate state
  const [isDeactivateOpen, setIsDeactivateOpen] = useState(false)
  const [deactivatePassword, setDeactivatePassword] = useState("")
  const [isDeactivating, setIsDeactivating] = useState(false)

  useEffect(() => {
    if (user) {
      setUsername(user.username || "")
      setEmail(user.email || "")
    }
  }, [user])

  const userInitial = (user?.username?.[0] || "U").toUpperCase()

  // Handle profile update (Name & Email)
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedUsername = username.trim()
    const trimmedEmail = email.trim()

    if (!trimmedUsername) {
      toast.error("Username cannot be empty")
      return
    }

    setIsSavingProfile(true)
    try {
      const res = await authUpdateProfile({
        username: trimmedUsername,
        email: trimmedEmail || null,
      })
      if (res.ok) {
        queryClient.setQueryData(["me"], res.data)
        queryClient.invalidateQueries({ queryKey: ["me"] })
        toast.success("Profile updated successfully")
      } else {
        toast.error(res.error?.detail || "Failed to update profile")
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update profile"
      toast.error(msg)
    } finally {
      setIsSavingProfile(false)
    }
  }

  // Handle password change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!currentPassword) {
      toast.error("Please enter your current password")
      return
    }

    if (newPassword.length < 6) {
      toast.error("New password must be at least 6 characters")
      return
    }

    if (newPassword !== confirmPassword) {
      toast.error("New passwords do not match")
      return
    }

    setIsChangingPassword(true)
    try {
      const res = await authChangePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      if (res.ok) {
        toast.success("Password changed successfully")
        setCurrentPassword("")
        setNewPassword("")
        setConfirmPassword("")
      } else {
        toast.error(res.error?.detail || "Failed to change password")
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to change password"
      toast.error(msg)
    } finally {
      setIsChangingPassword(false)
    }
  }

  // Handle account deactivation
  const handleDeactivateAccount = async () => {
    setIsDeactivating(true)
    try {
      const res = await authDeactivateAccount({
        password: deactivatePassword || null,
      })
      if (res.ok) {
        queryClient.clear()
        toast.success("Account deactivated successfully")
        setIsDeactivateOpen(false)
        router.replace("/login")
      } else {
        toast.error(res.error?.detail || "Failed to deactivate account")
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to deactivate account"
      toast.error(msg)
    } finally {
      setIsDeactivating(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 rounded-2xl border border-border/80 bg-card shadow-xs">
        <div className="flex items-center gap-4">
          <Avatar className="size-16 ring-2 ring-primary/20">
            <AvatarFallback className="text-xl font-bold bg-primary/10 text-primary">
              {userInitial}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-heading">
              {user?.username || (isUserLoading ? "Loading..." : "User Profile")}
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground flex items-center gap-1.5">
              <MailIcon className="size-3.5" />
              {user?.email || "No email linked"}
            </p>
          </div>
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircle2Icon className="size-3.5" />
          <span>Active Vault</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Profile Info Card */}
        <Card className="border-border/80 shadow-xs flex flex-col justify-between">
          <div>
            <CardHeader>
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <UserIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">Personal Information</CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Update your account name and email address
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form id="profile-form" onSubmit={handleUpdateProfile} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="username" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Name / Username
                  </Label>
                  <Input
                    id="username"
                    name="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    disabled={isSavingProfile || isUserLoading}
                    required
                    minLength={3}
                    maxLength={32}
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Must be 3-32 characters: letters, numbers, dot, dash, underscore.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    disabled={isSavingProfile || isUserLoading}
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Used for notifications, deadline alerts, and digest updates.
                  </p>
                </div>
              </form>
            </CardContent>
          </div>
          <CardFooter className="border-t border-border/60 bg-muted/20 px-6 py-3.5 flex justify-end">
            <Button
              type="submit"
              form="profile-form"
              size="sm"
              disabled={isSavingProfile || isUserLoading}
              className="gap-2"
            >
              {isSavingProfile && <Loader2Icon className="size-3.5 animate-spin" />}
              Save Changes
            </Button>
          </CardFooter>
        </Card>

        {/* Change Password Card */}
        <Card className="border-border/80 shadow-xs flex flex-col justify-between">
          <div>
            <CardHeader>
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <KeyRoundIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">Change Password</CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Ensure your account stays secure with a strong password
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form id="password-form" onSubmit={handleChangePassword} className="space-y-3.5">
                <div className="space-y-1.5">
                  <Label htmlFor="current-password" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Current Password
                  </Label>
                  <Input
                    id="current-password"
                    name="current-password"
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="••••••••"
                    disabled={isChangingPassword}
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="new-password" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    New Password
                  </Label>
                  <Input
                    id="new-password"
                    name="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 6 characters"
                    disabled={isChangingPassword}
                    required
                    minLength={6}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="confirm-password" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Confirm New Password
                  </Label>
                  <Input
                    id="confirm-password"
                    name="confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    disabled={isChangingPassword}
                    required
                  />
                </div>
              </form>
            </CardContent>
          </div>
          <CardFooter className="border-t border-border/60 bg-muted/20 px-6 py-3.5 flex justify-end">
            <Button
              type="submit"
              form="password-form"
              size="sm"
              disabled={isChangingPassword}
              className="gap-2"
            >
              {isChangingPassword && <Loader2Icon className="size-3.5 animate-spin" />}
              Update Password
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* Danger Zone: Deactivate Account */}
      <Card className="border-destructive/30 bg-destructive/5 shadow-xs">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-destructive/10 text-destructive">
              <ShieldAlertIcon className="size-4" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold text-destructive">
                Danger Zone
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-0.5">
                Permanently deactivate your account and erase all associated vault data
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                Deactivate this account
              </p>
              <p className="text-xs text-muted-foreground max-w-xl">
                Once deactivated, all your uploaded documents, processed vector embeddings, AI summaries, reminders, and chat history will be permanently deleted. This action cannot be undone.
              </p>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setIsDeactivateOpen(true)}
              className="shrink-0 cursor-pointer"
            >
              Deactivate Account
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Deactivation Confirmation Dialog */}
      <Dialog open={isDeactivateOpen} onOpenChange={setIsDeactivateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="size-10 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mb-2">
              <AlertTriangleIcon className="size-5" />
            </div>
            <DialogTitle className="text-lg font-bold">Deactivate Account?</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground space-y-2 pt-1">
              <span>
                Are you sure you want to deactivate your account? All your local documents, memories, embeddings, and chat transcripts will be completely deleted from this machine.
              </span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 py-2">
            <Label htmlFor="deactivate-password" className="text-xs font-semibold text-muted-foreground">
              Confirm your password (optional):
            </Label>
            <Input
              id="deactivate-password"
              type="password"
              value={deactivatePassword}
              onChange={(e) => setDeactivatePassword(e.target.value)}
              placeholder="Enter password to confirm"
              disabled={isDeactivating}
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDeactivateOpen(false)}
              disabled={isDeactivating}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDeactivateAccount}
              disabled={isDeactivating}
              className="gap-2"
            >
              {isDeactivating && <Loader2Icon className="size-3.5 animate-spin" />}
              Yes, Deactivate Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
