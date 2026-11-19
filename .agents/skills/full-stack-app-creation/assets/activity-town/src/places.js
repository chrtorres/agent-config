export const places = {
  office: {
    name: 'Town Hall', detail: 'Office & cubicles', icon: 'office', color: 'violet',
    marker: [0, 10.65, -1.5], door: [0, 4.95]
  },
  documents: {
    name: 'Documents', detail: 'Files & research', icon: 'folder', color: 'mint',
    marker: [-17, 7.5, 0], door: [-17, 4.25]
  },
  pictures: {
    name: 'My Pictures', detail: 'Images & visual work', icon: 'picture', color: 'pink',
    marker: [16, 8.2, -4], door: [13.62, -.32]
  },
  workshop: {
    name: 'Workshop', detail: 'Code & tools', icon: 'tool', color: 'gold',
    marker: [12, 7.4, 10], door: [12, 14.2]
  }
};

const center = [0, 7.5];
const junction = [6.2, 7.5];
const paths = {
  office: [center, places.office.door],
  documents: [center, [-17, 7.5], places.documents.door],
  pictures: [center, junction, [6.2, 3.5], [13.62, 3.5], places.pictures.door],
  workshop: [center, junction, [6.2, 16], [12, 16], places.workshop.door]
};

const distance = ([ax, az], [bx, bz]) => Math.hypot(ax - bx, az - bz);
const lengthOf = (points) => points.reduce((length, point, index) => (
  index ? length + distance(points[index - 1], point) : length
), 0);

function projection([x, z], [ax, az], [bx, bz]) {
  const dx = bx - ax;
  const dz = bz - az;
  const offset = Math.min(1, Math.max(0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)));
  return [ax + dx * offset, az + dz * offset];
}

export function routeTo(current, destination) {
  let bestDistance = Infinity;
  let bestRoute = [];
  const target = paths[destination];
  // Every walkway has a single parent. From the nearest segment, either end can lead to the destination.
  for (const path of Object.values(paths)) {
    for (let index = 1; index < path.length; index++) {
      const point = projection(current, path[index - 1], path[index]);
      const offPath = distance(current, point);
      for (const end of [index - 1, index]) {
        const start = path.slice(0, end + 1);
        const shared = start.findLastIndex((node, index) => target[index] === node);
        const points = [point, ...start.slice(shared).reverse(), ...target.slice(shared + 1)];
        const score = offPath * 100 + lengthOf(points);
        if (score < bestDistance) {
          bestDistance = score;
          bestRoute = points;
        }
      }
    }
  }
  return bestRoute;
}
