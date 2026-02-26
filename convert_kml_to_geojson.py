import os
import glob
import json
import xml.etree.ElementTree as ET


def extract_polygon_coords(polygon_element, ns):
    """Extract coordinates from a Polygon element."""
    # We ideally want the outer boundary
    coords_elem = polygon_element.find(".//kml:outerBoundaryIs//kml:coordinates", ns)
    if coords_elem is None:
        coords_elem = polygon_element.find(".//outerBoundaryIs//coordinates")

    if coords_elem is None:
        # Fallback to any coordinates inside the polygon
        coords_elem = polygon_element.find(".//kml:coordinates", ns)
    if coords_elem is None:
        coords_elem = polygon_element.find(".//coordinates")

    if coords_elem is None or not coords_elem.text:
        return None

    coord_text = coords_elem.text.strip()
    coords = []

    for pair in coord_text.split():
        parts = pair.split(",")
        if len(parts) >= 2:
            lon = float(parts[0])
            lat = float(parts[1])
            coords.append([lon, lat])

    # GeoJSON requires first/last point to match
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])

    if not coords:
        return None

    return [coords]


def kml_to_geojson(data_dir, output_file):
    features = []
    kml_files = glob.glob(os.path.join(data_dir, "*.kml"))

    print(f"Found {len(kml_files)} KML files.")

    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    for kml_file in kml_files:
        basename = os.path.basename(kml_file)
        zone_code = os.path.splitext(basename)[0]

        try:
            tree = ET.parse(kml_file)
            root = tree.getroot()

            # Find all placemarks
            placemarks = root.findall(".//kml:Placemark", ns)
            if not placemarks:
                placemarks = root.findall(".//Placemark")

            for placemark in placemarks:
                # Some placemarks might have a name or description we can pull
                pm_name_elem = placemark.find(".//kml:name", ns)
                if pm_name_elem is None:
                    pm_name_elem = placemark.find(".//name")

                pm_name = pm_name_elem.text if pm_name_elem is not None else ""

                # A single placemark can have multiple Polygons inside a MultiGeometry
                polygons = placemark.findall(".//kml:Polygon", ns)
                if not polygons:
                    polygons = placemark.findall(".//Polygon")

                for polygon in polygons:
                    coords = extract_polygon_coords(polygon, ns)
                    if coords:
                        feature = {
                            "type": "Feature",
                            "properties": {"zona": zone_code, "name": pm_name},
                            "geometry": {"type": "Polygon", "coordinates": coords},
                        }
                        features.append(feature)
        except Exception as e:
            print(f"Error parsing {kml_file}: {e}")

    geojson = {"type": "FeatureCollection", "features": features}

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(geojson, f)

    print(f"Generated {output_file} with {len(features)} features.")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    output_file = os.path.join(current_dir, "frontend", "public", "zones.geojson")

    kml_to_geojson(data_dir, output_file)
