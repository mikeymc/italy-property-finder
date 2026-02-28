import { useState, useMemo } from 'react';
import MapGL, { Source, Layer, NavigationControl } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { calculateZoneMetrics } from '../utils/finance';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

export function ZoneMap({ zonesForLookup, onSelectZone, zoneOverrides, defaultParams }) {
    const [hoverInfo, setHoverInfo] = useState(null);

    // We are loading the big generated JSON.
    // We can fetch it or just tell Mapbox to load it from the public folder.
    const geojsonUrl = '/zones.geojson';

    // Fast lookup and color calc
    const { zoneLookup, fillColorExpression, strSampledNames } = useMemo(() => {
        const map = new Map();

        if (!zonesForLookup || zonesForLookup.length === 0 || !defaultParams) {
            return { zoneLookup: map, fillColorExpression: '#088', strSampledNames: new Set() };
        }

        const validYields = [];

        zonesForLookup.forEach(z => {
            const uniqueId = `${z.comune_name.toUpperCase()} - Zona OMI ${z.zona}`;
            // Avoid duplicate branch labels in the Mapbox match expression
            if (!map.has(uniqueId)) {
                map.set(uniqueId, z);
                const metrics = calculateZoneMetrics(z, defaultParams, zoneOverrides[uniqueId]);
                const yld = metrics ? metrics.gross_yield : null;
                if (yld !== null) {
                    validYields.push({ uniqueId, yld });
                }
            }
        });

        if (validYields.length === 0) {
            return { zoneLookup: map, fillColorExpression: '#088', strSampledNames: new Set() };
        }

        const colors = [
            '#d73027', // deep red
            '#fc8d59',
            '#fee08b',
            '#ffffbf', // neutral
            '#d9ef8b',
            '#91cf60',
            '#1a9850'  // deep green
        ];

        const matchExpr = ['match', ['get', 'name']];

        // Assign colors based on fixed yield ranges
        validYields.forEach((z) => {
            let colorIdx = 0;
            if (z.yld < 10) colorIdx = 0;
            else if (z.yld < 20) colorIdx = 1;
            else if (z.yld < 30) colorIdx = 2;
            else if (z.yld < 45) colorIdx = 3;
            else if (z.yld < 60) colorIdx = 4;
            else if (z.yld < 80) colorIdx = 5;
            else colorIdx = 6;

            matchExpr.push(z.uniqueId, colors[colorIdx]);
        });

        matchExpr.push('#cccccc'); // Fallback color

        // Mapbox match expression must have at least one label/value pair (so length >= 4)
        if (matchExpr.length < 4) {
            return { zoneLookup: map, fillColorExpression: '#088', strSampledNames: new Set() };
        }

        // Collect names of zones that have sampled STR data for border highlighting
        const strSampledNames = new Set(
            zonesForLookup
                .filter(z => z.has_str_data)
                .map(z => `${z.comune_name.toUpperCase()} - Zona OMI ${z.zona}`)
        );

        return { zoneLookup: map, fillColorExpression: matchExpr, strSampledNames };
    }, [zonesForLookup, zoneOverrides, defaultParams]);

    const fillLayerStyle = {
        id: 'zones-fill',
        type: 'fill',
        paint: {
            'fill-color': fillColorExpression,
            'fill-opacity': [
                'case',
                ['boolean', ['feature-state', 'hover'], false],
                0.9,
                0.6
            ]
        }
    };

    const lineLayerStyle = {
        id: 'zones-line',
        type: 'line',
        paint: {
            'line-color': '#000',
            'line-width': 0.5,
            'line-opacity': 0.2
        }
    };

    // Highlighted border for zones with real sampled STR data
    const sampledNamesArray = Array.from(strSampledNames || []);
    const strBorderLayerStyle = sampledNamesArray.length > 0 ? {
        id: 'zones-str-border',
        type: 'line',
        filter: ['in', ['get', 'name'], ['literal', sampledNamesArray]],
        paint: {
            'line-color': '#0066ff',
            'line-width': 1.5,
            'line-opacity': 0.8,
        }
    } : null;

    // Find full zone detail when clicked
    const handleMapClick = (event) => {
        const feature = event.features && event.features[0];
        if (feature) {
            const uniqueName = feature.properties.name;
            const matchedZone = zoneLookup.get(uniqueName) || { zona: uniqueName };
            onSelectZone(matchedZone);
        }
    };

    return (
        <div style={{ width: '100%', height: '100%', minHeight: '600px' }}>
            {!MAPBOX_TOKEN ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>Mapbox token is missing in .env</div>
            ) : (
                <MapGL
                    initialViewState={{
                        longitude: 12.5,
                        latitude: 42.5,
                        zoom: 5
                    }}
                    mapStyle="mapbox://styles/mapbox/light-v11"
                    mapboxAccessToken={MAPBOX_TOKEN}
                    interactiveLayerIds={['zones-fill']}
                    onClick={handleMapClick}
                    onMouseMove={(e) => {
                        const feature = e.features && e.features[0];
                        if (feature) {
                            const uniqueName = feature.properties.name;
                            const matchedZone = zoneLookup.get(uniqueName);
                            const metrics = matchedZone ? calculateZoneMetrics(matchedZone, defaultParams, zoneOverrides[uniqueName]) : null;
                            const yld = metrics ? metrics.gross_yield : null;

                            setHoverInfo({
                                x: e.point.x,
                                y: e.point.y,
                                zone: uniqueName,
                                yield: yld,
                                hasStrData: matchedZone?.has_str_data || false,
                                medianRate: matchedZone?.median_nightly_rate || null,
                            });
                        } else {
                            setHoverInfo(null);
                        }
                    }}
                    onMouseLeave={() => setHoverInfo(null)}
                >
                    <Source id="omi-zones" type="geojson" data={geojsonUrl} generateId={true}>
                        <Layer {...fillLayerStyle} />
                        <Layer {...lineLayerStyle} />
                        {strBorderLayerStyle && <Layer {...strBorderLayerStyle} />}
                    </Source>

                    <NavigationControl position="bottom-right" />

                    {hoverInfo && (
                        <div
                            style={{
                                position: 'absolute',
                                left: hoverInfo.x,
                                top: hoverInfo.y,
                                transform: 'translate(-50%, -100%)',
                                marginTop: '-10px',
                                background: 'white',
                                padding: '6px 10px',
                                borderRadius: '4px',
                                pointerEvents: 'none',
                                boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                                fontSize: '13px',
                                zIndex: 10
                            }}
                        >
                            <div style={{ fontWeight: 'bold', borderBottom: '1px solid #ddd', paddingBottom: '4px', marginBottom: '4px' }}>
                                Zone: {hoverInfo.zone}
                            </div>
                            <div style={{ color: hoverInfo.yield !== null && hoverInfo.yield > 0 ? '#1a9850' : '#888', fontWeight: hoverInfo.yield !== null && hoverInfo.yield > 0 ? 'bold' : 'normal' }}>
                                {hoverInfo.yield !== null && hoverInfo.yield !== undefined ? `Yield: ${hoverInfo.yield.toFixed(1)}%` : 'Yield: N/A'}
                            </div>
                            {hoverInfo.hasStrData && hoverInfo.medianRate && (
                                <div style={{ color: '#0066ff', fontSize: '12px', marginTop: '2px' }}>
                                    ● Sampled: €{Math.round(hoverInfo.medianRate)}/night
                                </div>
                            )}
                        </div>
                    )}
                </MapGL>
            )}
        </div>
    );
}
