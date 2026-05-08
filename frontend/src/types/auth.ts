export type RoleName = string;
export type PermissionCode = string;

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
  };
}

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: RoleName[];
  permissions: PermissionCode[];
}
