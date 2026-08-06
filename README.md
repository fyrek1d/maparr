# Maparr

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-green.svg)](https://hub.docker.com/r/maparr/maparr)

> **Maparr** is a self-hosted offline map manager for homeserver users. It provides an easy-to-use web interface to download, manage, and serve map data entirely from your local server—no internet connection required after downloading maps.

![Screenshot](docs/screenshots/maparr-viewer.svg)

## ✨ Features

### Admin Interface
- **Map Providers**: Choose from multiple map data sources (OpenStreetMap, CartoDB, OpenTopoMap, satellite imagery, and more)
- **Region Selection**: Download by country, state, city, or custom bounding boxes
- **Download Management**: Pause, resume, cancel downloads with real-time progress tracking
- **Storage Management**: View storage usage by region, verify map integrity, clean up unused areas
- **User Management**: Role-based access control with local and optional LDAP/OIDC authentication
- **Layer Management**: Enable/disable map layers per region (satellite, topo, trails, etc.)
- **Backups & Maintenance**: Automated backups, integrity checks, and scheduled maintenance

### User Interface
- **Offline-First Map Viewer**: Instant loading, smooth panning/zooming
- **Local Search**: Search locations using offline geocoding database
- **Bookmarks & Markers**: Save favorite locations, custom pins, named markers
- **GPX Support**: Import/export GPX tracks and waypoints
- **Measurement Tools**: Measure distances and areas
- **Shareable Links**: Share map views with other users on the same server
- **Print Maps**: Generate printable maps of your current view
- **Dark Mode**: Optional dark theme for comfortable viewing

### Technical Features
- **Docker-First**: Single-container deployment with multi-arch support
- **REST API**: Full API for automation and integrations
- **Webhooks**: Event notifications for download completion, updates, etc.
- **Observability**: Prometheus metrics, structured logging, health monitoring
- **Low Resource Usage**: Optimized for Raspberry Pi-class hardware
- **Responsive Design**: Works on desktops, tablets, and mobile devices

## 🚀 Quick Start

### Docker Compose (Recommended)

```bash
git clone https://git.fyrek.dev/fyrek/maparr.git
cd maparr
docker compose up -d
```

Access the admin interface at `http://localhost:8080` and configure your first map download.

### Manual Installation

See [Installation Guide](docs/installation.md)

## 📚 Documentation

- [User Guide](docs/user-guide.md)
- [Admin Guide](docs/admin-guide.md)
- [API Documentation](docs/api.md)
- [Configuration](docs/configuration.md)
- [Environment Variables](docs/environment-variables.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🛠️ Development

See [Development Guide](docs/development.md)

## 📦 Map Providers

Maparr supports multiple map providers with offline licensing:

| Provider | Type | License | Offline |
|----------|------|---------|---------|
| OpenStreetMap | Basemap | ODbL | ✅ |
| OpenStreetMap HOT | Basemap | ODbL | ✅ |
| CartoDB Voyager | Basemap | CC BY-SA | ✅ |
| OpenTopoMap | Topographic | CC BY-SA | ✅ |
| CycleOSM | Cycling | ODbL | ✅ |
| Waymarked Trails | Overlay | ODbL | ✅ |
| Esri World Imagery | Satellite | Esri Terms | ⚠️ Check license |

### Custom Providers

You can add custom map providers via the admin interface:

```json
{
  "name": "My Custom Map",
  "url_template": "https://tiles.example.com/{z}/{x}/{y}.png",
  "attribution": "© My Map Provider",
  "license": "Custom License"
}
```

## 🔒 Authentication

Maparr supports multiple authentication methods:

- **Local Users**: Username/password with bcrypt hashing
- **OpenID Connect**: Connect to identity providers like Authelia, Keycloak
- **LDAP/Active Directory**: Integrate with existing directory services

## 📊 System Requirements

- **CPU**: 1 core minimum, 2+ recommended
- **RAM**: 512MB minimum, 1GB+ recommended
- **Storage**: 1GB minimum + map data (typically 1-10GB per region)
- **Network**: Initial setup only; works offline afterwards
- **OS**: Linux, Docker support (Windows/macOS via Docker)

## 🤝 Contributing

We welcome contributions! Please see [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Natural Earth](https://www.naturalearthdata.com/) for geographic data
- [Leaflet](https://leafletjs.com/) for the mapping library
- [OpenStreetMap](https://www.openstreetmap.org/) contributors
- All map data providers for their offline-friendly licenses

---

**Made with ❤️ for the self-hosting community**