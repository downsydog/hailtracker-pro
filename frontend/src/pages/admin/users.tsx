import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { adminApi } from "@/api/admin"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { User } from "@/types"
import { Plus, MoreHorizontal, Shield, ShieldOff } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function UsersPage() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => adminApi.getUsers(),
  })

  const toggleActive = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      adminApi.updateUser(id, { is_active: active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
    },
  })

  const users = data?.users || []

  const columns: Column<User>[] = [
    {
      key: "username",
      header: "Username",
      render: (user) => <span className="font-medium">{user.username}</span>,
    },
    {
      key: "name",
      header: "Name",
      render: (user) => user.name || "—",
    },
    {
      key: "email",
      header: "Email",
      render: (user) => user.email || "—",
    },
    {
      key: "role",
      header: "Role",
      render: (user) => (
        <Badge variant={user.role === "admin" ? "default" : "secondary"}>
          {user.role}
        </Badge>
      ),
    },
    {
      key: "is_active",
      header: "Status",
      render: (user) => (
        <Badge variant={user.is_active ? "outline" : "destructive"}>
          {user.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (user) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Edit User</DropdownMenuItem>
            <DropdownMenuItem>Reset Password</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() =>
                toggleActive.mutate({ id: user.id, active: !user.is_active })
              }
            >
              {user.is_active ? (
                <>
                  <ShieldOff className="mr-2 h-4 w-4" />
                  Deactivate
                </>
              ) : (
                <>
                  <Shield className="mr-2 h-4 w-4" />
                  Activate
                </>
              )}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        description="Manage user accounts and permissions."
        actions={[
          {
            label: "Add User",
            onClick: () => {
              // TODO: Open add user modal
            },
            icon: Plus,
          },
        ]}
      />

      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={users}
            isLoading={isLoading}
            emptyMessage="No users found"
            keyExtractor={(user) => user.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}
