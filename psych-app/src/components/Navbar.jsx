import { useState, useRef, useEffect } from "react";

const ChevronDown = ({ className }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 4.5L6 7.5L9 4.5" />
  </svg>
);

const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a0a5b1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" />
    <path d="M21 21l-4.35-4.35" />
  </svg>
);

const MenuIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);

const CloseIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

function useClickOutside(ref, handler) {
  useEffect(() => {
    const listener = (e) => {
      if (!ref.current || ref.current.contains(e.target)) return;
      handler();
    };
    document.addEventListener("mousedown", listener);
    return () => document.removeEventListener("mousedown", listener);
  }, [ref, handler]);
}

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [servicesOpen, setServicesOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [mobileLoginOpen, setMobileLoginOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const servicesRef = useRef(null);
  const loginRef = useRef(null);
  const mobileContentRef = useRef(null);
  const [mobileHeight, setMobileHeight] = useState(0);

  useEffect(() => {
    if (mobileOpen && mobileContentRef.current) {
      setMobileHeight(mobileContentRef.current.scrollHeight);
    } else {
      setMobileHeight(0);
    }
  }, [mobileOpen, servicesOpen, mobileLoginOpen]);

  useClickOutside(servicesRef, () => setServicesOpen(false));
  useClickOutside(loginRef, () => setLoginOpen(false));

  const navLinks = [
    { label: "Home", href: "#" },
    { label: "About", href: "#" },
  ];

  const services = [
    "Web Design",
    "Web Development",
    "Graphic Design",
    "Digital Marketing",
  ];

  const trailingLinks = [
    { label: "Pricing", href: "#", active: true },
    { label: "Blog", href: "#" },
    { label: "Contact", href: "#" },
  ];

  const linkClass = (active) =>
    `px-3 py-2 text-sm transition-colors duration-150 ${
      active
        ? "text-[#210AA1] font-semibold"
        : "text-[#888] hover:text-[#210AA1]"
    }`;

  return (
    <div
      style={{
        fontFamily: "'Varela Round', 'Nunito', sans-serif",
        flexShrink: 0,
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=Varela+Round&display=swap"
        rel="stylesheet"
      />

      <nav
        style={{
          background: "#fff",
          borderBottom: "1px solid #dfe3e8",
          padding: "0 16px",
          flexShrink: 0,
          zIndex: 1000,
        }}
        className="relative"
      >
        <div className="flex items-center justify-between h-14">
          {/* Brand */}
          <a
            href="#"
            className="text-xl no-underline flex-shrink-0"
            style={{ color: "#333", paddingRight: 50 }}
          >
            Brand<b style={{ color: "#210AA1" }}>Name</b>
          </a>

          {/* Mobile Toggle */}
          <button
            className="lg:hidden p-2 rounded"
            onClick={() => {
              const next = !mobileOpen;
              setMobileOpen(next);
              if (!next) {
                setServicesOpen(false);
                setMobileLoginOpen(false);
              }
            }}
            style={{ color: "#888" }}
          >
            {mobileOpen ? <CloseIcon /> : <MenuIcon />}
          </button>

          {/* Desktop Nav */}
          <div className="hidden lg:flex items-center flex-1">
            <div className="flex items-center">
              {navLinks.map((l) => (
                <a key={l.label} href={l.href} className={linkClass(false)}>
                  {l.label}
                </a>
              ))}

              {/* Services Dropdown */}
              <div ref={servicesRef} className="relative">
                <button
                  onClick={() => {
                    setServicesOpen(!servicesOpen);
                    setLoginOpen(false);
                  }}
                  className={`${linkClass(false)} flex items-center gap-1 cursor-pointer bg-transparent border-none outline-none`}
                >
                  Services
                  <ChevronDown
                    className={`transition-transform duration-200 ${
                      servicesOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {servicesOpen && (
                  <div
                    className="absolute top-full left-0 mt-1 bg-white rounded shadow-lg border z-50"
                    style={{
                      borderColor: "#e5e5e5",
                      boxShadow: "0 2px 8px rgba(0,0,0,.05)",
                      minWidth: 200,
                    }}
                  >
                    {services.map((s) => (
                      <a
                        key={s}
                        href="#"
                        className="block px-5 py-2 text-sm text-[#888] hover:bg-gray-50 hover:text-[#210AA1] no-underline transition-colors"
                      >
                        {s}
                      </a>
                    ))}
                  </div>
                )}
              </div>

              {trailingLinks.map((l) => (
                <a
                  key={l.label}
                  href={l.href}
                  className={linkClass(l.active)}
                >
                  {l.label}
                </a>
              ))}
            </div>

            {/* Search */}
            <div className="relative ml-8" style={{ width: 300 }}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search here..."
                className="w-full text-sm rounded outline-none"
                style={{
                  padding: "7px 35px 7px 12px",
                  border: "1px solid #dfe3e8",
                  boxShadow: "none",
                }}
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2">
                <SearchIcon />
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 ml-auto">
              {/* Login Dropdown */}
              <div ref={loginRef} className="relative">
                <button
                  onClick={() => {
                    setLoginOpen(!loginOpen);
                    setServicesOpen(false);
                  }}
                  className="text-sm bg-transparent border-none cursor-pointer px-3 py-2 outline-none"
                  style={{ color: "#888" }}
                >
                  Login
                </button>
                {loginOpen && (
                  <div
                    className="absolute top-full right-0 mt-1 bg-white rounded shadow-lg border z-50"
                    style={{
                      width: 280,
                      padding: 20,
                      borderColor: "#e5e5e5",
                      boxShadow: "0 2px 8px rgba(0,0,0,.05)",
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="mb-3">
                      <label
                        className="block text-sm mb-1"
                        style={{ color: "#888", fontWeight: "normal" }}
                      >
                        Username
                      </label>
                      <input
                        type="text"
                        required
                        className="w-full text-sm rounded outline-none"
                        style={{
                          padding: "7px 12px",
                          border: "1px solid #dfe3e8",
                        }}
                      />
                    </div>
                    <div className="mb-3">
                      <div className="flex justify-between items-center mb-1">
                        <label
                          className="text-sm"
                          style={{ color: "#888", fontWeight: "normal" }}
                        >
                          Password
                        </label>
                        <a
                          href="#"
                          className="text-xs no-underline hover:underline"
                          style={{ color: "#aaa" }}
                        >
                          Forgot?
                        </a>
                      </div>
                      <input
                        type="password"
                        required
                        className="w-full text-sm rounded outline-none"
                        style={{
                          padding: "7px 12px",
                          border: "1px solid #dfe3e8",
                        }}
                      />
                    </div>
                    <button
                      className="w-full text-sm text-white rounded cursor-pointer border-none"
                      style={{
                        background: "#210AA1",
                        padding: "9px 16px",
                      }}
                      onMouseEnter={(e) =>
                        (e.target.style.background = "#280CC2")
                      }
                      onMouseLeave={(e) =>
                        (e.target.style.background = "#210AA1")
                      }
                    >
                      Login
                    </button>
                  </div>
                )}
              </div>

              <a
                href="#"
                className="text-sm text-white no-underline rounded text-center"
                style={{
                  background: "#210AA1",
                  padding: "8px 20px",
                  minWidth: 120,
                }}
                onMouseEnter={(e) => (e.target.style.background = "#280CC2")}
                onMouseLeave={(e) => (e.target.style.background = "#210AA1")}
              >
                Get Started
              </a>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        <div
          className="lg:hidden overflow-hidden"
          style={{
            maxHeight: mobileHeight,
            transition: "max-height 0.35s ease",
          }}
        >
          <div
            ref={mobileContentRef}
            className="pb-2"
          >
            {/* Nav Links */}
            <div
              className="flex flex-col"
              style={{ borderBottom: "1px solid #eee" }}
            >
              {navLinks.map((l) => (
                <a
                  key={l.label}
                  href={l.href}
                  className="no-underline"
                  style={{
                    color: "#888",
                    fontSize: 15,
                    padding: "10px 16px",
                    borderTop: "1px solid #eee",
                  }}
                >
                  {l.label}
                </a>
              ))}

              {/* Mobile Services Dropdown */}
              <div>
                <button
                  onClick={() => setServicesOpen(!servicesOpen)}
                  className="w-full text-left flex items-center justify-between bg-transparent border-none cursor-pointer outline-none"
                  style={{
                    color: "#888",
                    fontSize: 15,
                    padding: "10px 16px",
                    borderTop: "1px solid #eee",
                  }}
                >
                  Services
                  <ChevronDown
                    className={`transition-transform duration-200 ${
                      servicesOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {servicesOpen && (
                  <div style={{ background: "#f8f8f8" }}>
                    {services.map((s) => (
                      <a
                        key={s}
                        href="#"
                        className="block no-underline"
                        style={{
                          color: "#888",
                          fontSize: 14,
                          padding: "8px 20px 8px 32px",
                          lineHeight: "normal",
                        }}
                      >
                        {s}
                      </a>
                    ))}
                  </div>
                )}
              </div>

              {trailingLinks.map((l) => (
                <a
                  key={l.label}
                  href={l.href}
                  className="no-underline"
                  style={{
                    color: l.active ? "#210AA1" : "#888",
                    fontWeight: l.active ? 600 : 400,
                    fontSize: 15,
                    padding: "10px 16px",
                    borderTop: "1px solid #eee",
                  }}
                >
                  {l.label}
                </a>
              ))}
            </div>

            {/* Search */}
            <div className="relative" style={{ padding: "12px 16px" }}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search here..."
                className="w-full rounded outline-none"
                style={{
                  fontSize: 15,
                  padding: "8px 35px 8px 12px",
                  border: "1px solid #dfe3e8",
                }}
              />
              <span className="absolute top-1/2 -translate-y-1/2" style={{ right: 28 }}>
                <SearchIcon />
              </span>
            </div>

            {/* Login Dropdown Toggle */}
            <div style={{ padding: "0 16px" }}>
              <button
                onClick={() => setMobileLoginOpen(!mobileLoginOpen)}
                className="w-full text-left flex items-center justify-between bg-transparent border-none cursor-pointer outline-none"
                style={{
                  color: "#888",
                  fontSize: 15,
                  padding: "10px 0",
                  borderTop: "1px solid #eee",
                }}
              >
                Login
                <ChevronDown
                  className={`transition-transform duration-200 ${
                    mobileLoginOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {/* Login Form (collapsible) */}
              {mobileLoginOpen && (
                <div style={{ padding: "8px 0 12px" }}>
                  <div className="mb-3">
                    <label
                      className="block mb-1"
                      style={{ color: "#888", fontWeight: "normal", fontSize: 14 }}
                    >
                      Username
                    </label>
                    <input
                      type="text"
                      required
                      className="w-full rounded outline-none"
                      style={{
                        fontSize: 14,
                        padding: "7px 12px",
                        border: "1px solid #dfe3e8",
                      }}
                    />
                  </div>
                  <div className="mb-3">
                    <div className="flex justify-between items-center mb-1">
                      <label
                        style={{ color: "#888", fontWeight: "normal", fontSize: 14 }}
                      >
                        Password
                      </label>
                      <a
                        href="#"
                        className="no-underline hover:underline"
                        style={{ color: "#aaa", fontSize: 12 }}
                      >
                        Forgot?
                      </a>
                    </div>
                    <input
                      type="password"
                      required
                      className="w-full rounded outline-none"
                      style={{
                        fontSize: 14,
                        padding: "7px 12px",
                        border: "1px solid #dfe3e8",
                      }}
                    />
                  </div>
                  <button
                    className="w-full text-white rounded cursor-pointer border-none"
                    style={{
                      background: "#210AA1",
                      fontSize: 14,
                      padding: "9px 16px",
                    }}
                  >
                    Login
                  </button>
                </div>
              )}
            </div>

            {/* Get Started CTA */}
            <div style={{ padding: "4px 16px 8px" }}>
              <a
                href="#"
                className="block text-white no-underline rounded text-center"
                style={{
                  background: "#210AA1",
                  fontSize: 15,
                  padding: "9px 16px",
                }}
              >
                Get Started
              </a>
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
}