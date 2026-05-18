module.exports = {
  apps: [
    {
      name: "outfitduel",
      // FastAPI app served by uvicorn under PM2.
      script: "uvicorn",
      args: "server:app --host 0.0.0.0 --port 3000 --workers 2 --proxy-headers --forwarded-allow-ips=*",
      interpreter: "python3",
      cwd: "./backend",
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
        // Real values live in /app/backend/.env (loaded via python-dotenv)
      },
      error_file: "./logs/outfitduel.err.log",
      out_file: "./logs/outfitduel.out.log",
      time: true,
    },
  ],
};
