// frontend/src/pages/settings/RolesSettings.tsx
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { PlusCircle, Trash2 } from 'lucide-react';
import { api } from '@/api/client';
import type {
  Permission,
  Role,
  RoleCreate,
  RoleUpdate,
  RoleWithPermissions,
} from '@/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import { Checkbox } from '@/components/ui/Checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/Separator';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

const roleSchema = z.object({
  name: z.string().min(1, 'Role name is required'),
  description: z.string().optional(),
  permissions: z.array(z.string()).optional(),
});

type RoleFormValues = z.infer<typeof roleSchema>;

export function RolesSettings() {
  const [roles, setRoles] = useState<RoleWithPermissions[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleWithPermissions | null>(
    null,
  );
  const [isModalOpen, setIsModalOpen] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
  });

  const watchedPermissions = watch('permissions') || [];

  useEffect(() => {
    fetchRolesAndPermissions();
  }, []);

  const fetchRolesAndPermissions = async () => {
    try {
      const [rolesData, permissionsData] = await Promise.all([
        api.get<Role[]>('/rbac/roles'),
        api.get<Permission[]>('/rbac/permissions'),
      ]);

      // Fetch full role details with permissions for each role
      const rolesWithPermissions = await Promise.all(
        rolesData.map((role) =>
          api.get<RoleWithPermissions>(`/rbac/roles/${role.id}`),
        ),
      );

      setRoles(rolesWithPermissions);
      setPermissions(permissionsData);
    } catch (error) {
      console.error('Failed to fetch roles or permissions:', error);
      toast.error('Failed to load roles or permissions.');
    }
  };

  const openModalForCreate = () => {
    setSelectedRole(null);
    reset({ name: '', description: '', permissions: [] });
    setIsModalOpen(true);
  };

  const openModalForEdit = (role: RoleWithPermissions) => {
    setSelectedRole(role);
    reset({
      name: role.name,
      description: role.description || '',
      permissions: role.permissions.map((p) => p.code),
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (values: RoleFormValues) => {
    try {
      if (selectedRole) {
        // Update role
        const updateData: RoleUpdate = {
          name: values.name,
          description: values.description,
          permissions: values.permissions,
        };
        await api.put(`/rbac/roles/${selectedRole.id}`, updateData);
        toast.success('Role updated successfully.');
      } else {
        // Create role
        const createData: RoleCreate = {
          name: values.name,
          description: values.description,
          permissions: values.permissions || [],
        };
        await api.post('/rbac/roles', createData);
        toast.success('Role created successfully.');
      }
      fetchRolesAndPermissions();
      setIsModalOpen(false);
    } catch (error) {
      console.error('Failed to save role:', error);
      toast.error('Failed to save role.');
    }
  };

  const onDelete = async (roleId: string) => {
    if (!confirm('Are you sure you want to delete this role?')) return;
    try {
      await api.delete(`/rbac/roles/${roleId}`);
      toast.success('Role deleted successfully.');
      fetchRolesAndPermissions();
    } catch (error) {
      console.error('Failed to delete role:', error);
      toast.error('Failed to delete role.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Role Management</h2>
        <Button onClick={openModalForCreate}>
          <PlusCircle className="mr-2 h-4 w-4" /> Create New Role
        </Button>
      </div>

      <Separator />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {roles.map((role) => (
          <Card key={role.id}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {role.name}
                {!role.is_system && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(role.id)}
                    aria-label={`Delete ${role.name}`}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                )}
              </CardTitle>
              <p className="text-sm text-gray-500">{role.description}</p>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {role.permissions.map((perm) => (
                  <span
                    key={perm.code}
                    className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10"
                  >
                    {perm.code}
                  </span>
                ))}
              </div>
              <Button
                variant="secondary"
                size="sm"
                className="mt-4 w-full"
                onClick={() => openModalForEdit(role)}
                disabled={role.is_system}
              >
                Edit Role
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>{selectedRole ? 'Edit Role' : 'Create Role'}</DialogTitle>
            <DialogDescription>
              {selectedRole
                ? 'Edit the details and permissions of this role.'
                : 'Create a new role and assign permissions.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                Name
              </Label>
              <Input
                id="name"
                {...register('name')}
                className="col-span-3"
                disabled={selectedRole?.is_system}
              />
              {errors.name && (
                <p className="col-span-4 col-start-2 text-sm text-red-500">
                  {errors.name.message}
                </p>
              )}
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="description" className="text-right">
                Description
              </Label>
              <Textarea
                id="description"
                {...register('description')}
                className="col-span-3"
              />
            </div>

            <Separator className="my-4" />

            <h3 className="text-lg font-semibold col-span-4">Permissions</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-60 overflow-y-auto border p-2 rounded-md">
              {permissions.map((perm) => (
                <div key={perm.code} className="flex items-center space-x-2">
                  <Checkbox
                    id={perm.code}
                    checked={
                      selectedRole?.is_system ||
                      watchedPermissions.includes(perm.code)
                    }
                    onCheckedChange={(checked: boolean) => {
                      if (checked) {
                        setValue(
                          'permissions',
                          [...watchedPermissions, perm.code],
                          { shouldValidate: true },
                        );
                      } else {
                        setValue(
                          'permissions',
                          watchedPermissions.filter((p) => p !== perm.code),
                          { shouldValidate: true },
                        );
                      }
                    }}
                    disabled={selectedRole?.is_system}
                  />
                  <Label htmlFor={perm.code} className="flex flex-col">
                    <span className="font-medium">{perm.code}</span>
                    <span className="text-xs text-gray-500">
                      {perm.description}
                    </span>
                  </Label>
                </div>
              ))}
            </div>

            <DialogFooter>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Save changes'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
