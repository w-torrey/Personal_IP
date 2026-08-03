--
PostgreSQL database dump
--

\restrict 0tVWMX1dkCNqaDScQVNMGgTDTYex7E7wBGHfmYKQL4Z6VSIluMjl6nVYKED329R

-- Dumped from database version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)
-- Dumped by pg_dump version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: digests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.digests (
    id integer NOT NULL,
    watchlist_id integer NOT NULL,
    headline text NOT NULL,
    narrative text NOT NULL,
    severity text NOT NULL,
    alert_ids jsonb,
    generated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT digests_severity_check CHECK ((severity = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text])))
);


ALTER TABLE public.digests OWNER TO postgres;

--
-- Name: digests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.digests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.digests_id_seq OWNER TO postgres;

--
-- Name: digests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.digests_id_seq OWNED BY public.digests.id;


--
-- Name: dossiers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dossiers (
    watchlist_id integer NOT NULL,
    summary text NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.dossiers OWNER TO postgres;

--
-- Name: results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.results (
    id integer NOT NULL,
    watchlist_id integer,
    title text,
    link text,
    snippet text,
    source character varying(255),
    date_found character varying(100),
    is_new boolean DEFAULT true,
    fetched_at timestamp without time zone DEFAULT now(),
    is_read boolean DEFAULT false NOT NULL
);


ALTER TABLE public.results OWNER TO postgres;

--
-- Name: results_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.results_id_seq OWNER TO postgres;

--
-- Name: results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.results_id_seq OWNED BY public.results.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    hashed_password text NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: watchlists; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.watchlists (
    id integer NOT NULL,
    person character varying(255),
    organization character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    category character varying(100) DEFAULT 'Uncategorized'::character varying,
    label character varying(255),
    query_params jsonb,
    name_aliases text[] DEFAULT '{}'::text[]
);


ALTER TABLE public.watchlists OWNER TO postgres;

--
-- Name: watchlists_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.watchlists_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.watchlists_id_seq OWNER TO postgres;

--
-- Name: watchlists_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.watchlists_id_seq OWNED BY public.watchlists.id;


--
-- Name: digests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.digests ALTER COLUMN id SET DEFAULT nextval('public.digests_id_seq'::regclass);


--
-- Name: results id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results ALTER COLUMN id SET DEFAULT nextval('public.results_id_seq'::regclass);


--
-- Name: watchlists id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.watchlists ALTER COLUMN id SET DEFAULT nextval('public.watchlists_id_seq'::regclass);


--
-- Name: digests digests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.digests
    ADD CONSTRAINT digests_pkey PRIMARY KEY (id);


--
-- Name: dossiers dossiers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dossiers
    ADD CONSTRAINT dossiers_pkey PRIMARY KEY (watchlist_id);


--
-- Name: results results_link_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_link_key UNIQUE (link);


--
-- Name: results results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: watchlists watchlists_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.watchlists
    ADD CONSTRAINT watchlists_pkey PRIMARY KEY (id);


--
-- Name: digests digests_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.digests
    ADD CONSTRAINT digests_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES public.watchlists(id) ON DELETE CASCADE;


--
-- Name: dossiers dossiers_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dossiers
    ADD CONSTRAINT dossiers_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES public.watchlists(id) ON DELETE CASCADE;


--
-- Name: results results_watchlist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_watchlist_id_fkey FOREIGN KEY (watchlist_id) REFERENCES public.watchlists(id);


--
-- PostgreSQL database dump complete
--
