import { useState, useMemo } from 'react';
import MapGL, { Source, Layer, NavigationControl } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { grossYield } from './ZoneExplorer';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

export function ZoneMap({ zonesForLookup, onSelectZone }) {
    const [hoverInfo, setHoverInfo] = useState(null);

    // We are loading the big generated JSON.
    // We can fetch it or just tell Mapbox to load it from the public folder.
    const geojsonUrl = '/zones.geojson';

    // Fast lookup and color calc
    const { zoneLookup, fillColorExpression } = useMemo(() => {
        const map = new Map();

        if (!zonesForLookup || zonesForLookup.length === 0) {
            return { zoneLookup: map, fillColorExpression: '#088' };
        }

        const validYields = [];

        zonesForLookup.forEach(z => {
            const uniqueId = `${z.comune_name.toUpperCase()} - Zona OMI ${z.zona}`;
            // Avoid duplicate branch labels in the Mapbox match expression
            if (!map.has(uniqueId)) {
                map.set(uniqueId, z);
                const yld = grossYield(z);
                if (yld !== null) {
                    validYields.push({ uniqueId, yld });
                }
            }
        });

        if (validYields.length === 0) {
            return { zoneLookup: map, fillColorExpression: '#088' };
        }

        // Sort ascending to easily compute rank/percentiles
        validYields.sort((a, b) => a.yld - b.yld);

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
        const n = validYields.length;

        // Assign colors based on percentile rank so we get an even distribution
        validYields.forEach((z, idx) => {
            let pct = idx / Math.max(1, n - 1);
            let colorIdx = Math.floor(pct * 6.99); // map to 0-6
            matchExpr.push(z.uniqueId, colors[colorIdx]);
        });

        matchExpr.push('#cccccc'); // Fallback color

        // Mapbox match expression must have at least one label/value pair (so length >= 4)
        if (matchExpr.length < 4) {
            return { zoneLookup: map, fillColorExpression: '#088' };
        }

        return { zoneLookup: map, fillColorExpression: matchExpr };
    }, [zonesForLookup]);

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
                            const yld = matchedZone ? grossYield(matchedZone) : null;

                            setHoverInfo({
                                x: e.point.x,
                                y: e.point.y,
                                zone: uniqueName,
                                yield: yld
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
                            <div style={{ color: hoverInfo.yield ? '#1a9850' : '#888', fontWeight: hoverInfo.yield ? 'bold' : 'normal' }}>
                                {hoverInfo.yield !== null ? `Yield: ${hoverInfo.yield.toFixed(1)}%` : 'Yield: N/A'}
                            </div>
                        </div>
                    )}
                </MapGL>
            )}
        </div>
    );
}
