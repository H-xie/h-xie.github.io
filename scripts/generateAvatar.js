const fs = require('fs');
const { execSync } = require('child_process');
const jdenticon = require('jdenticon');

// 获取最新 git commit hash，并与当前时间混合
function getBlendedHash() {
  let hash = '';
  try {
    hash = execSync('git rev-parse HEAD').toString().trim();
  } catch (error) {
    console.error('Error fetching git commit hash:', error);
    hash = 'default-hash';
  }
  // 获取当前时间字符串
  const now = new Date().toISOString();
  // 用 sha256 混合 hash 和时间
  const crypto = require('crypto');
  return crypto.createHash('sha256').update(hash + now).digest('hex');
}

// 生成 identicon SVG
function generateAvatar(hash) {
  // 100 为图片尺寸，可根据需要调整
  return jdenticon.toSvg(hash, 100);
}

// 保存 SVG 到文件
function saveAvatar(filePath) {
  const hash = getBlendedHash();
  const svg = generateAvatar(hash);
  fs.writeFileSync(filePath, svg);
  console.log(`Avatar saved to ${filePath}`);
}

// 用法
saveAvatar('./static/images/avatar.svg');