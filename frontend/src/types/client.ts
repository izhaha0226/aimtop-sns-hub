export interface Client {
  id: string;
  name: string;
  logo?: string;
  brand_color?: string;
  account_type?: string;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClientCreate {
  name: string;
  logo?: string;
  brand_color?: string;
  account_type?: string;
}
