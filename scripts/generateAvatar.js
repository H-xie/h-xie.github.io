const fs = require('fs');
const crypto = require('crypto');
const { execSync } = require('child_process');

// Function to get the latest git commit hash
function getLatestGitHash() {
  try {
    return execSync('git rev-parse HEAD').toString().trim();
  } catch (error) {
    console.error('Error fetching git commit hash:', error);
    return 'default-hash'; // Fallback in case of error
  }
}

// Function to generate an identicon-style avatar SVG
function generateAvatar(hash) {
  const size = 100; // 10x10 grid for more detail
  const cellSize = 10; // Size of each cell in pixels
  const colors = [`#${hash.substring(0, 6)}`, `#${hash.substring(6, 12)}`]; // Two colors based on hash

  let svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size * cellSize}" height="${size * cellSize}" viewBox="0 0 ${size * cellSize} ${size * cellSize}">
      <rect width="${size * cellSize}" height="${size * cellSize}" fill="${colors[0]}"/>
    </svg>
  `;

  // Generate the grid pattern
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < Math.ceil(size / 2); x++) {
      const value = parseInt(hash[(y * size + x) % hash.length], 16);
      if (value % 2 === 0) {
        const fillColor = colors[1];
        const rectX = x * cellSize;
        const rectY = y * cellSize;

        // Mirror the pattern horizontally
        svg += `<rect x="${rectX}" y="${rectY}" width="${cellSize}" height="${cellSize}" fill="${fillColor}"/>`;
        svg += `<rect x="${(size - x - 1) * cellSize}" y="${rectY}" width="${cellSize}" height="${cellSize}" fill="${fillColor}"/>`;
      }
    }
  }

  svg += '</svg>';
  return svg;
}

// Save the SVG to a file
function saveAvatar(filePath) {
  const hash = getLatestGitHash();
  const svg = generateAvatar(hash);
  fs.writeFileSync(filePath, svg);
  console.log(`Avatar saved to ${filePath}`);
}

// Example usage
saveAvatar('./static/images/avatar.svg');