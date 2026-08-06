import Leaflet from 'leaflet';

declare module 'leaflet' {
  namespace Icon {
    interface Default {
      _getIconUrl?: never;
    }
  }
}
