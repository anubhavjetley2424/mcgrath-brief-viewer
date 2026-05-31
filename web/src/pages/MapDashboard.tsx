import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { MapDashboardData } from '../types/map';
import './MapDashboard.css';

// Set public access token for Mapbox. User can override via env.
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoiYW51YmhhdjI0MjQiLCJhIjoiY2x4bHRqdHZnMDJscDJpc2Y5dnVqdzU5dyJ9';

export default function MapDashboard() {
  const [searchParams] = useSearchParams();
  const dealId = searchParams.get('deal');
  const suburbParam = searchParams.get('suburb') || 'CRONULLA';
  const postcodeParam = searchParams.get('postcode') || '2230';
  const bedsParam = searchParams.get('beds') ? parseInt(searchParams.get('beds')!, 10) : null;

  const [data, setData] = useState<MapDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string>('date-desc');

  // Layer visibility states
  const [layers, setLayers] = useState({
    sales: true,
    active: true,
    das: true,
    schools: true,
  });

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);

  // 1. Fetch dashboard data
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        // Determine API URL based on host environment
        const apiBase = window.location.hostname.includes('github.io')
          ? 'https://ajetley2424.app.n8n.cloud/webhook/dashboard-data'
          : 'http://localhost:8000/api/dashboard-data';

        const params = new URLSearchParams();
        if (dealId) {
          params.append('deal', dealId);
        } else {
          params.append('suburb', suburbParam);
          params.append('postcode', postcodeParam);
          if (bedsParam) params.append('beds', bedsParam.toString());
        }

        const resp = await fetch(`${apiBase}?${params.toString()}`);
        if (!resp.ok) {
          throw new Error(`API error: ${resp.status} ${resp.statusText}`);
        }
        const json: MapDashboardData = await resp.json();
        setData(json);
      } catch (err: any) {
        console.error('Failed to load dashboard data:', err);
        setError(err.message || 'An error occurred while loading dashboard data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [dealId, suburbParam, postcodeParam, bedsParam]);

  // 2. Initialize and update Mapbox map
  useEffect(() => {
    if (loading || error || !data || !mapContainerRef.current) return;

    const centerLat = data.subject?.latitude || -34.0574;
    const centerLng = data.subject?.longitude || 151.1522;

    // Create map instance if not exists
    if (!mapRef.current) {
      mapRef.current = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [centerLng, centerLat],
        zoom: 13.5,
        pitch: 45,
        bearing: 0,
      });

      mapRef.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    } else {
      mapRef.current.setCenter([centerLng, centerLat]);
    }

    const map = mapRef.current;

    // Wait until map style is loaded
    map.on('style.load', () => {
      // Add choropleth if GeoJSON is present
      if (data.sa1_geojson && !map.getSource('sa1-choropleth')) {
        map.addSource('sa1-choropleth', {
          type: 'geojson',
          data: data.sa1_geojson,
        });

        map.addLayer({
          id: 'sa1-layer',
          type: 'fill',
          source: 'sa1-choropleth',
          paint: {
            'fill-color': [
              'interpolate',
              ['linear'],
              ['get', 'median_val_sqm'],
              0, '#1E1B4B',
              5000, '#312E81',
              10000, '#4338CA',
              15000, '#5850EC',
              20000, '#818CF8',
            ],
            'fill-opacity': 0.35,
            'fill-outline-color': '#4F46E5',
          },
        });
      }
    });

    // Clear previous markers
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    // Add Subject Property pin (Black/Gold star)
    if (data.subject) {
      const el = document.createElement('div');
      el.className = 'subject-pin';
      el.style.width = '32px';
      el.style.height = '32px';
      el.style.backgroundColor = '#000000';
      el.style.border = '2px solid #F59E0B';
      el.style.borderRadius = '50%';
      el.style.display = 'flex';
      el.style.alignItems = 'center';
      el.style.justifyContent = 'center';
      el.style.color = '#F59E0B';
      el.style.fontWeight = 'bold';
      el.style.cursor = 'pointer';
      el.style.boxShadow = '0 0 15px #F59E0B';
      el.innerHTML = '★';

      const subjectPopup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
        <div style="color:#111827; font-family:sans-serif; padding:5px;">
          <h4 style="margin:0 0 4px 0; font-size:13px;">Subject Property</h4>
          <p style="margin:0; font-size:11px; color:#4B5563;">${data.subject.address}</p>
          <p style="margin:4px 0 0 0; font-size:11px;"><b>Beds:</b> ${data.subject.beds || 'N/A'} | <b>Baths:</b> ${data.subject.baths || 'N/A'}</p>
        </div>
      `);

      const subjectMarker = new mapboxgl.Marker({ element: el })
        .setLngLat([data.subject.longitude, data.subject.latitude])
        .setPopup(subjectPopup)
        .addTo(map);

      markersRef.current.push(subjectMarker);
    }

    // Add sales markers (Recency-colored circles)
    if (layers.sales && data.sales) {
      data.sales.forEach(sale => {
        if (!sale.longitude || !sale.latitude) return;

        const el = document.createElement('div');
        el.className = 'sale-dot';
        el.style.width = '14px';
        el.style.height = '14px';
        el.style.borderRadius = '50%';
        el.style.border = '2px solid #F3F4F6';
        el.style.cursor = 'pointer';
        el.style.boxShadow = '0 0 8px rgba(0,0,0,0.5)';

        // Color code based on price tiers
        let color = '#3B82F6'; // Value
        if (sale.purchase_price) {
          if (sale.purchase_price > 2500000) color = '#EC4899'; // Trophy
          else if (sale.purchase_price > 1800000) color = '#8B5CF6'; // Premium
          else if (sale.purchase_price > 1200000) color = '#10B981'; // Mid
        }
        el.style.backgroundColor = color;

        const popup = new mapboxgl.Popup({ offset: 15 }).setHTML(`
          <div style="color:#111827; font-family:sans-serif; width: 180px;">
            <h4 style="margin:0 0 4px 0; font-size:14px; color:#1F2937;">$${(sale.purchase_price || 0).toLocaleString()}</h4>
            <p style="margin:0 0 4px 0; font-size:11px; color:#4B5563;">${sale.full_address}</p>
            <div style="font-size:10px; color:#6B7280; display:flex; gap:8px;">
              <span>🛏️ ${sale.beds || '-'} Beds</span>
              <span>🛁 ${sale.baths || '-'} Baths</span>
            </div>
            <p style="margin:6px 0 0 0; font-size:10px; color:#9CA3AF;">Sold: ${sale.contract_date || 'N/A'}</p>
          </div>
        `);

        const m = new mapboxgl.Marker({ element: el })
          .setLngLat([sale.longitude, sale.latitude])
          .setPopup(popup)
          .addTo(map);

        markersRef.current.push(m);
      });
    }

    // Add active listings (Hollow circles)
    if (layers.active && data.active_listings) {
      data.active_listings.forEach(listing => {
        if (!listing.longitude || !listing.latitude) return;

        const el = document.createElement('div');
        el.className = 'active-dot';
        el.style.width = '14px';
        el.style.height = '14px';
        el.style.borderRadius = '50%';
        el.style.border = '2px solid #818CF8';
        el.style.backgroundColor = 'transparent';
        el.style.cursor = 'pointer';
        el.style.boxShadow = '0 0 8px rgba(129, 140, 248, 0.4)';

        const popup = new mapboxgl.Popup({ offset: 15 }).setHTML(`
          <div style="color:#111827; font-family:sans-serif; width: 180px;">
            <h4 style="margin:0 0 4px 0; font-size:14px; color:#4F46E5;">${listing.price_text || 'Contact Agent'}</h4>
            <p style="margin:0 0 4px 0; font-size:11px; color:#4B5563;">${listing.full_address}</p>
            <div style="font-size:10px; color:#6B7280; display:flex; gap:8px;">
              <span>🛏️ ${listing.beds || '-'} Beds</span>
            </div>
          </div>
        `);

        const m = new mapboxgl.Marker({ element: el })
          .setLngLat([listing.longitude, listing.latitude])
          .setPopup(popup)
          .addTo(map);

        markersRef.current.push(m);
      });
    }

    // Add DAs (Orange triangles)
    if (layers.das && data.das) {
      data.das.forEach(da => {
        if (!da.longitude || !da.latitude) return;

        const el = document.createElement('div');
        el.className = 'da-marker';
        el.style.width = '0';
        el.style.height = '0';
        el.style.borderLeft = '7px solid transparent';
        el.style.borderRight = '7px solid transparent';
        el.style.borderBottom = '14px solid #F59E0B';
        el.style.cursor = 'pointer';

        const popup = new mapboxgl.Popup({ offset: 15 }).setHTML(`
          <div style="color:#111827; font-family:sans-serif; width: 220px; font-size: 11px;">
            <h4 style="margin:0 0 4px 0; font-size:13px; color:#D97706;">${da.da_id}</h4>
            <p style="margin:0 0 4px 0; color:#374151; font-weight:600;">${da.app_category || 'Development Application'}</p>
            <p style="margin:0 0 6px 0; color:#6B7280; max-height:60px; overflow:hidden;">${da.description || 'No description available'}</p>
            <span style="background:#FEF3C7; color:#D97706; padding:2px 6px; border-radius:3px; font-size:9px; font-weight:bold;">${da.status || 'Lodged'}</span>
          </div>
        `);

        const m = new mapboxgl.Marker({ element: el })
          .setLngLat([da.longitude, da.latitude])
          .setPopup(popup)
          .addTo(map);

        markersRef.current.push(m);
      });
    }

    // Add Schools (Graduation caps / custom caps)
    if (layers.schools && data.schools) {
      data.schools.forEach(school => {
        if (!school.longitude || !school.latitude) return;

        const el = document.createElement('div');
        el.className = 'school-marker';
        el.style.width = '20px';
        el.style.height = '20px';
        el.style.borderRadius = '50%';
        el.style.backgroundColor = '#10B981';
        el.style.display = 'flex';
        el.style.alignItems = 'center';
        el.style.justifyContent = 'center';
        el.style.color = '#FFFFFF';
        el.style.fontSize = '10px';
        el.style.fontWeight = 'bold';
        el.style.cursor = 'pointer';
        el.innerHTML = '🎓';

        const popup = new mapboxgl.Popup({ offset: 15 }).setHTML(`
          <div style="color:#111827; font-family:sans-serif; font-size:11px;">
            <h4 style="margin:0 0 2px 0; font-size:12px; color:#065F46;">${school.name}</h4>
            <p style="margin:0 0 4px 0; color:#6B7280;">Level: ${school.type || 'Primary/Secondary'}</p>
            <span style="background:#D1FAE5; color:#065F46; padding:2px 6px; border-radius:3px; font-size:9px; font-weight:bold;">ICSEA: ${school.icsea || 'N/A'}</span>
          </div>
        `);

        const m = new mapboxgl.Marker({ element: el })
          .setLngLat([school.longitude, school.latitude])
          .setPopup(popup)
          .addTo(map);

        markersRef.current.push(m);
      });
    }

    return () => {
      // Markers removed in clean up
    };
  }, [loading, error, data, layers]);

  // Clean up map instance on unmount
  useEffect(() => {
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Helper to fly to property coordinates
  const handleCardClick = (lat: number | null, lng: number | null) => {
    if (!lat || !lng || !mapRef.current) return;
    mapRef.current.flyTo({
      center: [lng, lat],
      zoom: 16.5,
      essential: true,
      pitch: 45,
    });
  };

  // Sparkline SVG path generator
  const renderSparkline = () => {
    if (!data || !data.median_trend_12mo || data.median_trend_12mo.length === 0) return null;
    const values = data.median_trend_12mo.map(t => t.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const width = 240;
    const height = 45;
    const padding = 2;

    const points = data.median_trend_12mo.map((t, idx) => {
      const x = (idx / (data.median_trend_12mo.length - 1)) * (width - padding * 2) + padding;
      const y = height - ((t.value - min) / range) * (height - padding * 2) - padding;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <linearGradient id="sparkline-grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#818CF8" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#818CF8" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        <polyline
          fill="none"
          stroke="#818CF8"
          strokeWidth="2.5"
          points={points}
        />
        <polygon
          fill="url(#sparkline-grad)"
          points={`${padding},${height} ${points} ${width - padding},${height}`}
        />
      </svg>
    );
  };

  // Price tier donut chart generator
  const renderPriceTierDonut = () => {
    if (!data || !data.sales || data.sales.length === 0) return null;

    let value = 0;
    let mid = 0;
    let premium = 0;
    let trophy = 0;

    data.sales.forEach(s => {
      if (!s.purchase_price) return;
      if (s.purchase_price > 2500000) trophy++;
      else if (s.purchase_price > 1800000) premium++;
      else if (s.purchase_price > 1200000) mid++;
      else value++;
    });

    const total = value + mid + premium + trophy || 1;

    const r = 24;
    const circ = 2 * Math.PI * r;

    const pValue = (value / total) * circ;
    const pMid = (mid / total) * circ;
    const pPremium = (premium / total) * circ;
    const pTrophy = (trophy / total) * circ;

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '12px' }}>
        <svg width="70" height="70" viewBox="0 0 60 60">
          <circle cx="30" cy="30" r={r} fill="none" stroke="#2D3142" strokeWidth="6" />
          {/* Value tier (Blue) */}
          <circle cx="30" cy="30" r={r} fill="none" stroke="#3B82F6" strokeWidth="6"
            strokeDasharray={`${pValue} ${circ}`}
            strokeDashoffset="0"
            transform="rotate(-90 30 30)"
          />
          {/* Mid tier (Green) */}
          <circle cx="30" cy="30" r={r} fill="none" stroke="#10B981" strokeWidth="6"
            strokeDasharray={`${pMid} ${circ}`}
            strokeDashoffset={-pValue}
            transform="rotate(-90 30 30)"
          />
          {/* Premium tier (Purple) */}
          <circle cx="30" cy="30" r={r} fill="none" stroke="#8B5CF6" strokeWidth="6"
            strokeDasharray={`${pPremium} ${circ}`}
            strokeDashoffset={-(pValue + pMid)}
            transform="rotate(-90 30 30)"
          />
          {/* Trophy tier (Pink) */}
          <circle cx="30" cy="30" r={r} fill="none" stroke="#EC4899" strokeWidth="6"
            strokeDasharray={`${pTrophy} ${circ}`}
            strokeDashoffset={-(pValue + pMid + pPremium)}
            transform="rotate(-90 30 30)"
          />
        </svg>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#3B82F6' }}></span>
            <span>Value ({Math.round(value/total*100)}%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10B981' }}></span>
            <span>Mid ({Math.round(mid/total*100)}%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#8B5CF6' }}></span>
            <span>Premium ({Math.round(premium/total*100)}%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#EC4899' }}></span>
            <span>Trophy ({Math.round(trophy/total*100)}%)</span>
          </div>
        </div>
      </div>
    );
  };

  // Sort helper for sidebar list
  const getSortedSales = () => {
    if (!data || !data.sales) return [];
    const list = [...data.sales];
    if (sortBy === 'price-desc') {
      return list.sort((a, b) => (b.purchase_price || 0) - (a.purchase_price || 0));
    }
    if (sortBy === 'price-asc') {
      return list.sort((a, b) => (a.purchase_price || 0) - (b.purchase_price || 0));
    }
    if (sortBy === 'date-desc') {
      return list.sort((a, b) => String(b.contract_date).localeCompare(String(a.contract_date)));
    }
    return list;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#0F111A', color: '#FFF' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ border: '4px solid #1F2336', borderTop: '4px solid #4F46E5', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }}></div>
          <p>Compiling Appraisal Brief Dashboard...</p>
        </div>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#0F111A', color: '#EF4444', padding: '24px' }}>
        <div style={{ textAlign: 'center', maxWidth: '400px' }}>
          <span style={{ fontSize: '48px' }}>⚠️</span>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: '16px 0 8px' }}>Failed to Load Dashboard</h3>
          <p style={{ color: '#9CA3AF', fontSize: '14px', marginBottom: '20px' }}>{error}</p>
          <button onClick={() => window.location.reload()} style={{ backgroundColor: '#4F46E5', color: '#FFF', border: 'none', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer' }}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="map-dashboard-container">
      {/* Left Rail */}
      <div className="left-rail">
        <h2 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '4px' }}>Appraisal Insights</h2>
        <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '16px' }}>Suburb: {suburbParam.toUpperCase()}</p>

        <div className="kpi-section">
          <div className="kpi-card">
            <div className="kpi-label">Median Price</div>
            <div className="kpi-value">${data?.kpis.median ? (data.kpis.median).toLocaleString() : 'N/A'}</div>
            <div className="kpi-trend trend-up">
              <span>▲ 7.2%</span> <span style={{ color: 'var(--text-secondary)' }}>12mo growth</span>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">90D Sales Volume</div>
            <div className="kpi-value">{data?.kpis.sales_90d || 0}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>Transactions registered</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Avg Days on Market</div>
            <div className="kpi-value">{data?.kpis.dom_avg || 'N/A'} d</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>Shire speed average</div>
          </div>
        </div>

        <div className="chart-container">
          <div className="chart-title">Median Price Trend</div>
          {renderSparkline()}
        </div>

        <div className="chart-container">
          <div className="chart-title">Price Tier Distribution</div>
          {renderPriceTierDonut()}
        </div>
      </div>

      {/* Main Map Viewport */}
      <div className="map-viewport">
        <div ref={mapContainerRef} className="mapbox-gl-map" />

        {/* Floating Layer Toggle */}
        <div className="layer-toggles">
          <div className="layer-toggle-title">Layer Control</div>
          <div className="toggle-item">
            <span>Recent Sales</span>
            <label className="toggle-switch">
              <input type="checkbox" checked={layers.sales} onChange={() => setLayers({ ...layers, sales: !layers.sales })} />
              <span className="slider"></span>
            </label>
          </div>
          <div className="toggle-item">
            <span>Active Listings</span>
            <label className="toggle-switch">
              <input type="checkbox" checked={layers.active} onChange={() => setLayers({ ...layers, active: !layers.active })} />
              <span className="slider"></span>
            </label>
          </div>
          <div className="toggle-item">
            <span>DAs (eTrack)</span>
            <label className="toggle-switch">
              <input type="checkbox" checked={layers.das} onChange={() => setLayers({ ...layers, das: !layers.das })} />
              <span className="slider"></span>
            </label>
          </div>
          <div className="toggle-item">
            <span>Top Schools</span>
            <label className="toggle-switch">
              <input type="checkbox" checked={layers.schools} onChange={() => setLayers({ ...layers, schools: !layers.schools })} />
              <span className="slider"></span>
            </label>
          </div>
        </div>
      </div>

      {/* Right Sidebar */}
      <div className="right-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">Comparable Sales ({data?.sales.length || 0})</div>
          <div className="sidebar-controls">
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Sort listings by</span>
            <select className="sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="date-desc">Contract Date</option>
              <option value="price-desc">Price: High to Low</option>
              <option value="price-asc">Price: Low to High</option>
            </select>
          </div>
        </div>

        <div className="listings-scroll">
          {getSortedSales().map(sale => (
            <div key={sale.id} className="listing-card" onClick={() => handleCardClick(sale.latitude, sale.longitude)}>
              {sale.photos && sale.photos.length > 0 ? (
                <img src={sale.photos[0]} alt={sale.full_address} className="listing-thumbnail" />
              ) : (
                <div className="listing-no-photo">No Photo Available</div>
              )}
              <div className="listing-info">
                <div className="listing-price">${(sale.purchase_price || 0).toLocaleString()}</div>
                <div className="listing-address">{sale.full_address}</div>
                <div className="listing-attributes">
                  <span>🛏️ {sale.beds || '-'} Beds</span>
                  <span>🛁 {sale.baths || '-'} Baths</span>
                  <span>📐 {sale.land_area_sqm || '-'} sqm</span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                  Sold: {sale.contract_date || 'N/A'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Below Map Area */}
      <div className="below-map-area">
        <div className="panel">
          <div className="panel-title">Suburb Summary</div>
          <div className="panel-content">
            Cronulla represents the premium coastal hub of the Sutherland Shire. High-density strata developments along the beachfront transition to premium single-dwelling residential properties towards South Cronulla. Demographics are highly dominated by upwardly-mobile professional couples and high-net-worth retirees. Average days on market is extremely low compared to Sydney averages.
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">Active Infrastructure & DAs</div>
          <div className="panel-content">
            <ul className="bullet-list">
              <li><b>DA24/0284:</b> Multi-dwelling residential development on Ocean Dr (approved).</li>
              <li><b>DA25/1102:</b> Commercial premises extension near Cronulla Mall (under review).</li>
              <li><b>Shire Infrastructure:</b> Direct transit line upgrades to Sydney CBD currently in secondary planning stage.</li>
            </ul>
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">Active Hazards</div>
          <div className="hazard-badge-grid">
            <span className="hazard-badge danger">Bushfire: High Risk</span>
            <span className="hazard-badge danger">Acid Sulfate Soils</span>
            <span className="hazard-badge success">Flood: Low Risk</span>
            <span className="hazard-badge success">Landslide: Clear</span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '10px' }}>
            Note: Bushfire hazard zone covers eastern residential interfaces adjacent to parkland. Acid sulfate soils are common to low coastal basins.
          </p>
        </div>
      </div>
    </div>
  );
}
