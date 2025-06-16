// app/page.tsx
import ESP32Controller from '@/components/ESP32Controller';

export default function Home() {
  return (
    <main className="min-h-screen bg-black">
      <div className="mx-auto px-24 py-16 w-full">
        <ESP32Controller />
      </div>
    </main>
  );
}