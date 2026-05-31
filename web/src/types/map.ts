export interface Sale {
  id: number;
  latitude: number | null;
  longitude: number | null;
  full_address: string;
  purchase_price: number | null;
  contract_date: string | null;
  beds: number | null;
  baths: number | null;
  land_area_sqm: number | null;
  property_type: string | null;
  suburb: string;
  photo_url: string | null;
  photos: string[] | null;
}

export interface ActiveListing {
  id: number;
  latitude: number | null;
  longitude: number | null;
  full_address: string;
  price_text: string | null;
  beds: number | null;
  baths: number | null;
  photo_url: string | null;
  photos: string[] | null;
}

export interface DA {
  id: number | string;
  da_id: string;
  latitude: number | null;
  longitude: number | null;
  full_address: string;
  app_category: string | null;
  app_subcategory: string | null;
  lodged_date: string | null;
  status: string | null;
  description: string | null;
}

export interface School {
  name: string;
  latitude: number | null;
  longitude: number | null;
  icsea: number | null;
  type: string | null;
}

export interface SubjectProperty {
  address: string;
  latitude: number;
  longitude: number;
  beds: number | null;
  baths: number | null;
}

export interface KPIs {
  median: number | null;
  sales_90d: number;
  dom_avg: number | null;
  growth_12mo_pct: number | null;
  active_count: number;
}

export interface MedianTrend {
  month: string;
  value: number;
}

export interface MapDashboardData {
  subject: SubjectProperty | null;
  sales: Sale[];
  active_listings: ActiveListing[];
  das: DA[];
  medians: Record<string, number> | null;
  median_trend_12mo: MedianTrend[];
  schools: School[];
  sa1_geojson: any | null; // GeoJSON.FeatureCollection | null
  kpis: KPIs;
}
